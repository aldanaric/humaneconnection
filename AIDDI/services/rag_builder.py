"""Build the local Humane Connection hybrid RAG index from source documents.

The builder intentionally uses only local libraries and creates both sparse TF-IDF
vectors and dense LSA vectors. A full rebuild is used because adding or removing
source material can change the shared vocabulary and SVD projection space.
"""
from __future__ import annotations

import csv
import os
import hashlib
import json
import math
import re
import sqlite3
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree as ET


# Keep local embedding rebuilds memory-stable in Docker/WSL. These variables
# must be set before importing NumPy, SciPy, or scikit-learn. Override them from
# one app-specific setting so inherited host defaults cannot unexpectedly create
# many BLAS workers and exhaust the container's memory.
_numeric_threads = os.getenv("RAG_NUMERIC_THREADS", "1").strip() or "1"
for _thread_env in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
):
    os.environ[_thread_env] = _numeric_threads

import joblib
import numpy as np
from pypdf import PdfReader
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


SCHEMA_VERSION = 2
INDEX_METHOD = "tfidf-lsa-hybrid-v2"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

TARGET_WORDS = 220
MAX_WORDS = 300
OVERLAP_WORDS = 40
MAX_FEATURES = 10_000
DENSE_DIMENSIONS = 128

BUILD_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "index_method": INDEX_METHOD,
    "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
    "chunking": {
        "target_words": TARGET_WORDS,
        "max_words": MAX_WORDS,
        "overlap_words": OVERLAP_WORDS,
    },
    "vectorizer": {
        "analyzer": "word",
        "ngram_range": [1, 2],
        "max_features": MAX_FEATURES,
        "sublinear_tf": True,
        "strip_accents": "unicode",
    },
    "dense": {
        "method": "TruncatedSVD followed by L2 normalization",
        "requested_dimensions": DENSE_DIMENSIONS,
        "random_state": 42,
    },
}


class RAGBuildError(RuntimeError):
    """Raised when an index cannot be built safely."""


class SparseIdentityProjector:
    """Fallback projector for very small corpora where SVD cannot be fitted."""

    def transform(self, matrix: sparse.spmatrix) -> np.ndarray:
        return matrix.toarray()


@dataclass(frozen=True)
class SourceRecord:
    relative_path: str
    absolute_path: Path
    extension: str
    sha256: str
    size_bytes: int
    modified_ns: int

    def as_manifest_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "extension": self.extension,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "modified_ns": self.modified_ns,
        }


@dataclass
class BuildResult:
    output_dir: Path
    source_files_seen: int
    source_files_indexed: int
    duplicate_files_skipped: int
    failed_files: int
    chunks: int
    dense_dimensions: int
    sparse_dimensions: int
    manifest: dict[str, Any]


_HEADING_RE = re.compile(
    r"^(?:"
    r"(?:section|phase|part|step|chapter|module|video)\s+[ivxlcdm\d]+(?:\s*[:\-–—].*)?"
    r"|opening|closing|conclusion|summary|key takeaways|what are .+|who are .+"
    r")$",
    flags=re.IGNORECASE,
)

_BOILERPLATE_PATTERNS = [
    re.compile(r"^©\s*\d{4}", re.IGNORECASE),
    re.compile(r"^https?://(?:www\.)?16personalities\.com/?$", re.IGNORECASE),
    re.compile(r"^knowledge base\s+theory\s+country profiles$", re.IGNORECASE),
    re.compile(r"^take (?:our )?free personality test", re.IGNORECASE),
    re.compile(r"^what(?:'|’)s your (?:role|strategy)\??$", re.IGNORECASE),
    re.compile(r"^read more about .+\.?$", re.IGNORECASE),
    re.compile(r"^\d+$"),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_config_fingerprint() -> str:
    encoded = json.dumps(BUILD_CONFIG, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def discover_sources(source_dir: str | Path) -> list[SourceRecord]:
    root = Path(source_dir).expanduser().resolve()
    if not root.exists():
        return []

    records: list[SourceRecord] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        extension = path.suffix.casefold()
        if extension not in SUPPORTED_EXTENSIONS:
            continue
        stat = path.stat()
        records.append(
            SourceRecord(
                relative_path=path.relative_to(root).as_posix(),
                absolute_path=path,
                extension=extension.lstrip("."),
                sha256=sha256_file(path),
                size_bytes=stat.st_size,
                modified_ns=stat.st_mtime_ns,
            )
        )
    return records


def source_snapshot(source_dir: str | Path) -> list[dict[str, Any]]:
    return [record.as_manifest_dict() for record in discover_sources(source_dir)]


def snapshot_fingerprint(snapshot: Sequence[dict[str, Any]]) -> str:
    stable = [
        {
            "relative_path": item["relative_path"],
            "sha256": item["sha256"],
            "size_bytes": item["size_bytes"],
        }
        for item in sorted(snapshot, key=lambda value: value["relative_path"])
    ]
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _normalize_text(value: str) -> str:
    value = value.replace("\u00ad", "").replace("\u200b", "")
    value = value.replace("\uf0b7", "•").replace("\u2011", "-")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    return value.strip()


def _is_boilerplate(line: str) -> bool:
    normalized = _normalize_text(line)
    if not normalized:
        return True
    return any(pattern.search(normalized) for pattern in _BOILERPLATE_PATTERNS)


def _looks_like_heading(text: str, style: str | None = None) -> bool:
    text = _normalize_text(text)
    if not text or len(text) > 120:
        return False
    if style and style.casefold().startswith(("heading", "title", "subtitle")):
        return True
    if text.startswith("#"):
        return True
    if _HEADING_RE.match(text):
        return True
    generic_colon_leads = {
        "for example",
        "examples include",
        "that may include",
        "you might ask",
        "you are listening for",
        "you are looking for",
        "this can occur through",
        "participants are introduced to",
    }
    if (
        text.endswith(":")
        and len(text.split()) <= 10
        and text.rstrip(":").casefold() not in generic_colon_leads
    ):
        return True
    if re.match(
        r"^The .+ (?:Role|Strategy|Method|Doctrine|Model|Framework|Protocol)$",
        text,
    ):
        return True
    if text.isupper() and 1 < len(text.split()) <= 10:
        return True
    return False


def _clean_heading(text: str) -> str:
    return re.sub(r"^#{1,6}\s*", "", _normalize_text(text)).strip(": ")


def _extract_docx(path: Path) -> list[dict[str, Any]]:
    try:
        with zipfile.ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise RAGBuildError(f"Invalid DOCX file: {path.name}") from exc

    root = ET.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[dict[str, Any]] = []
    current_section: str | None = None
    number = 0

    for paragraph in root.findall(".//w:body//w:p", namespace):
        text = _normalize_text(
            "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        )
        if not text or _is_boilerplate(text):
            continue

        number += 1
        style_node = paragraph.find("./w:pPr/w:pStyle", namespace)
        style = None
        if style_node is not None:
            style = style_node.attrib.get(f"{{{namespace['w']}}}val")

        if _looks_like_heading(text, style):
            current_section = _clean_heading(text)

        paragraphs.append(
            {
                "text": text,
                "section": current_section,
                "page": None,
                "paragraph": number,
            }
        )

    return paragraphs


def _pdf_page_lines(reader: PdfReader) -> list[list[str]]:
    page_lines: list[list[str]] = []
    for page in reader.pages:
        raw_text = page.extract_text() or ""
        lines = [_normalize_text(line) for line in raw_text.splitlines()]
        page_lines.append([line for line in lines if line])
    return page_lines


def _repeated_pdf_lines(page_lines: Sequence[Sequence[str]]) -> set[str]:
    if len(page_lines) < 2:
        return set()
    occurrences: Counter[str] = Counter()
    for lines in page_lines:
        occurrences.update(set(lines))
    threshold = max(2, math.ceil(len(page_lines) * 0.5))
    return {
        line
        for line, count in occurrences.items()
        if count >= threshold and len(line) <= 160
    }


def _extract_pdf(path: Path) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pypdf exposes several parser-specific exceptions
        raise RAGBuildError(f"Unable to read PDF: {path.name}") from exc

    page_lines = _pdf_page_lines(reader)
    repeated = _repeated_pdf_lines(page_lines)
    units: list[dict[str, Any]] = []
    current_section: str | None = None

    for page_number, lines in enumerate(page_lines, start=1):
        for line in lines:
            if _is_boilerplate(line):
                continue
            if line in repeated and page_number > 1:
                continue
            if _looks_like_heading(line):
                current_section = _clean_heading(line)
            units.append(
                {
                    "text": line,
                    "section": current_section,
                    "page": page_number,
                    "paragraph": None,
                }
            )
    return units


def _extract_plain_text(path: Path) -> list[dict[str, Any]]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")

    units: list[dict[str, Any]] = []
    current_section: str | None = None
    paragraph_number = 0
    for block in re.split(r"\n\s*\n|^(?=#{1,6}\s)", content, flags=re.MULTILINE):
        text = _normalize_text(block)
        if not text or _is_boilerplate(text):
            continue
        paragraph_number += 1
        first_line = text.splitlines()[0] if text.splitlines() else text
        if _looks_like_heading(first_line):
            current_section = _clean_heading(first_line)
        units.append(
            {
                "text": text,
                "section": current_section,
                "page": None,
                "paragraph": paragraph_number,
            }
        )
    return units


def extract_units(record: SourceRecord) -> list[dict[str, Any]]:
    suffix = record.absolute_path.suffix.casefold()
    if suffix == ".docx":
        return _extract_docx(record.absolute_path)
    if suffix == ".pdf":
        return _extract_pdf(record.absolute_path)
    if suffix in {".txt", ".md"}:
        return _extract_plain_text(record.absolute_path)
    raise RAGBuildError(f"Unsupported source type: {record.relative_path}")


def _word_count(text: str) -> int:
    return len(text.split())


def _split_long_unit(unit: dict[str, Any], max_words: int) -> list[dict[str, Any]]:
    words = unit["text"].split()
    if len(words) <= max_words:
        return [unit]
    parts: list[dict[str, Any]] = []
    for start in range(0, len(words), max_words):
        clone = dict(unit)
        clone["text"] = " ".join(words[start : start + max_words])
        parts.append(clone)
    return parts


def _overlap_tail(units: Sequence[dict[str, Any]], overlap_words: int) -> list[dict[str, Any]]:
    if not units or overlap_words <= 0:
        return []
    remaining = overlap_words
    selected: list[dict[str, Any]] = []
    for unit in reversed(units):
        words = unit["text"].split()
        if not words:
            continue
        clone = dict(unit)
        if len(words) > remaining:
            clone["text"] = " ".join(words[-remaining:])
            selected.append(clone)
            remaining = 0
            break
        selected.append(clone)
        remaining -= len(words)
        if remaining <= 0:
            break
    selected.reverse()
    return selected


def _chunk_from_units(
    source: SourceRecord,
    units: Sequence[dict[str, Any]],
    duplicate_sources: Sequence[str],
) -> dict[str, Any]:
    text = "\n".join(unit["text"] for unit in units).strip()
    pages = [unit["page"] for unit in units if unit.get("page") is not None]
    paragraphs = [
        unit["paragraph"] for unit in units if unit.get("paragraph") is not None
    ]
    sections = [unit.get("section") for unit in units if unit.get("section")]
    section = sections[-1] if sections else None
    id_material = "|".join(
        [
            source.relative_path,
            str(min(pages) if pages else min(paragraphs) if paragraphs else ""),
            text,
        ]
    )
    chunk_id = hashlib.sha256(id_material.encode("utf-8")).hexdigest()[:20]
    return {
        "id": chunk_id,
        "text": text,
        "source": source.relative_path,
        "source_type": source.extension,
        "section": section,
        "page_start": min(pages) if pages else None,
        "page_end": max(pages) if pages else None,
        "paragraph_start": min(paragraphs) if paragraphs else None,
        "paragraph_end": max(paragraphs) if paragraphs else None,
        "word_count": _word_count(text),
        "char_count": len(text),
        "duplicate_sources": list(duplicate_sources),
    }


def chunk_units(
    source: SourceRecord,
    units: Sequence[dict[str, Any]],
    duplicate_sources: Sequence[str],
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for unit in units:
        expanded.extend(_split_long_unit(unit, MAX_WORDS))

    chunks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_words = 0

    def emit() -> None:
        nonlocal current, current_words
        if not current:
            return
        chunks.append(_chunk_from_units(source, current, duplicate_sources))
        current = _overlap_tail(current, OVERLAP_WORDS)
        current_words = sum(_word_count(unit["text"]) for unit in current)

    for unit in expanded:
        words = _word_count(unit["text"])
        if current and current_words >= TARGET_WORDS and current_words + words > MAX_WORDS:
            emit()
        elif current and current_words + words > MAX_WORDS:
            emit()

        current.append(unit)
        current_words += words

        if current_words >= MAX_WORDS:
            emit()

    if current:
        final_chunk = _chunk_from_units(source, current, duplicate_sources)
        # Avoid a tiny overlap-only tail when it is substantially contained in the prior chunk.
        if not chunks or final_chunk["word_count"] >= max(50, OVERLAP_WORDS + 10):
            chunks.append(final_chunk)

    return chunks


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_metadata_csv(path: Path, chunks: Sequence[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "source",
        "source_type",
        "section",
        "page_start",
        "page_end",
        "paragraph_start",
        "paragraph_end",
        "word_count",
        "char_count",
        "duplicate_sources",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for chunk in chunks:
            row = {key: chunk.get(key) for key in fieldnames}
            row["duplicate_sources"] = "; ".join(chunk.get("duplicate_sources", []))
            writer.writerow(row)


def _write_source_inventory(
    path: Path,
    records: Sequence[SourceRecord],
    canonical_by_hash: dict[str, str],
    errors: dict[str, str],
    chunk_counts: Counter[str],
) -> None:
    fieldnames = [
        "source",
        "extension",
        "size_bytes",
        "sha256",
        "status",
        "canonical_source",
        "chunks",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            canonical = canonical_by_hash[record.sha256]
            if record.relative_path in errors:
                status = "failed"
            elif record.relative_path != canonical:
                status = "duplicate_skipped"
            else:
                status = "indexed"
            writer.writerow(
                {
                    "source": record.relative_path,
                    "extension": record.extension,
                    "size_bytes": record.size_bytes,
                    "sha256": record.sha256,
                    "status": status,
                    "canonical_source": canonical,
                    "chunks": chunk_counts.get(canonical, 0),
                    "error": errors.get(record.relative_path, ""),
                }
            )


def _write_sqlite(
    path: Path,
    chunks: Sequence[dict[str, Any]],
    records: Sequence[SourceRecord],
) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE chunks (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                section TEXT,
                page_start INTEGER,
                page_end INTEGER,
                paragraph_start INTEGER,
                paragraph_end INTEGER,
                word_count INTEGER NOT NULL,
                text TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE sources (
                relative_path TEXT PRIMARY KEY,
                extension TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_ns INTEGER NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk["id"],
                    chunk["source"],
                    chunk["source_type"],
                    chunk.get("section"),
                    chunk.get("page_start"),
                    chunk.get("page_end"),
                    chunk.get("paragraph_start"),
                    chunk.get("paragraph_end"),
                    chunk["word_count"],
                    chunk["text"],
                )
                for chunk in chunks
            ],
        )
        connection.executemany(
            "INSERT INTO sources VALUES (?, ?, ?, ?, ?)",
            [
                (
                    record.relative_path,
                    record.extension,
                    record.sha256,
                    record.size_bytes,
                    record.modified_ns,
                )
                for record in records
            ],
        )
        connection.commit()
    finally:
        connection.close()


def _write_checksums(output_dir: Path) -> None:
    lines: list[str] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        lines.append(f"{sha256_file(path)}  {path.name}")
    (output_dir / "checksums.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def build_index(source_dir: str | Path, output_dir: str | Path) -> BuildResult:
    """Build a complete index in ``output_dir``.

    The caller should provide an empty temporary directory and atomically promote
    it only after this function succeeds.
    """
    source_root = Path(source_dir).expanduser().resolve()
    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if any(output_root.iterdir()):
        raise RAGBuildError(f"Build output directory is not empty: {output_root}")

    records = discover_sources(source_root)
    if not records:
        raise RAGBuildError(
            f"No supported documents found in {source_root}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    grouped: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in records:
        grouped[record.sha256].append(record)

    canonical_by_hash: dict[str, str] = {}
    canonical_records: list[SourceRecord] = []
    duplicate_names: dict[str, list[str]] = {}
    for digest, group in sorted(grouped.items(), key=lambda item: item[1][0].relative_path):
        group = sorted(group, key=lambda record: record.relative_path)
        canonical = group[0]
        canonical_by_hash[digest] = canonical.relative_path
        canonical_records.append(canonical)
        duplicate_names[canonical.relative_path] = [
            record.relative_path for record in group[1:]
        ]

    chunks: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    chunk_counts: Counter[str] = Counter()
    for record in canonical_records:
        try:
            units = extract_units(record)
            if not units:
                raise RAGBuildError("No extractable text was found.")
            source_chunks = chunk_units(
                record,
                units,
                duplicate_sources=duplicate_names[record.relative_path],
            )
            if not source_chunks:
                raise RAGBuildError("No usable chunks were produced.")
            chunks.extend(source_chunks)
            chunk_counts[record.relative_path] = len(source_chunks)
        except Exception as exc:
            errors[record.relative_path] = str(exc)

    indexed_records = [
        record for record in canonical_records if record.relative_path not in errors
    ]
    if not chunks:
        details = "; ".join(f"{name}: {error}" for name, error in errors.items())
        raise RAGBuildError(f"No source documents could be indexed. {details}")

    texts = [chunk["text"] for chunk in chunks]
    vectorizer = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=MAX_FEATURES,
        min_df=1,
        max_df=1.0,
        sublinear_tf=True,
        strip_accents="unicode",
        lowercase=True,
        token_pattern=r"(?u)\b[\w][\w'’-]+\b",
        dtype=np.float32,
    )
    tfidf = vectorizer.fit_transform(texts)
    if tfidf.shape[1] == 0:
        raise RAGBuildError("The corpus produced an empty TF-IDF vocabulary.")

    if min(tfidf.shape) > 1:
        dense_dimensions = min(DENSE_DIMENSIONS, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
        dense_dimensions = max(1, dense_dimensions)
        projector: Any = TruncatedSVD(
            n_components=dense_dimensions,
            algorithm="randomized",
            random_state=42,
        )
        dense = projector.fit_transform(tfidf)
    else:
        projector = SparseIdentityProjector()
        dense = projector.transform(tfidf)
        dense_dimensions = dense.shape[1]

    dense = normalize(dense, norm="l2").astype(np.float32)
    if not np.isfinite(dense).all():
        raise RAGBuildError("Dense vectors contain non-finite values.")

    _write_jsonl(output_root / "chunks.jsonl", chunks)
    _write_metadata_csv(output_root / "metadata.csv", chunks)
    _write_source_inventory(
        output_root / "source_inventory.csv",
        records,
        canonical_by_hash,
        errors,
        chunk_counts,
    )
    np.save(output_root / "embeddings.npy", dense)
    sparse.save_npz(output_root / "tfidf_matrix.npz", tfidf)
    joblib.dump(vectorizer, output_root / "tfidf_vectorizer.joblib")
    joblib.dump(projector, output_root / "svd_model.joblib")
    _write_sqlite(output_root / "rag_store.sqlite", chunks, records)

    snapshot = [record.as_manifest_dict() for record in records]
    manifest: dict[str, Any] = {
        "bundle_name": "Humane Connection Managed RAG Index",
        "schema_version": SCHEMA_VERSION,
        "index_method": INDEX_METHOD,
        "created_at_utc": utc_now_iso(),
        "source_directory": str(source_root),
        "source_snapshot": snapshot,
        "source_snapshot_fingerprint": snapshot_fingerprint(snapshot),
        "build_config": BUILD_CONFIG,
        "build_config_fingerprint": build_config_fingerprint(),
        "source_files_seen": len(records),
        "source_files_indexed": len(indexed_records),
        "source_files_duplicate_skipped": len(records) - len(canonical_records),
        "source_files_failed": len(errors),
        "failed_sources": errors,
        "chunks": len(chunks),
        "dense_embedding_method": (
            "TF-IDF word 1-2 grams followed by TruncatedSVD (LSA) and L2 normalization"
        ),
        "dense_dimensions": int(dense.shape[1]),
        "sparse_dimensions": int(tfidf.shape[1]),
        "retrieval_default": "hybrid cosine: 0.65 sparse TF-IDF + 0.35 dense LSA",
        "validation": {
            "chunk_vector_alignment": (
                len(chunks) == tfidf.shape[0] == dense.shape[0]
            ),
            "dense_vectors_finite": bool(np.isfinite(dense).all()),
            "dense_norm_mean": float(np.linalg.norm(dense, axis=1).mean()),
            "dense_norm_min": float(np.linalg.norm(dense, axis=1).min()),
            "dense_norm_max": float(np.linalg.norm(dense, axis=1).max()),
        },
        "created_files": [
            "chunks.jsonl",
            "metadata.csv",
            "source_inventory.csv",
            "embeddings.npy",
            "tfidf_matrix.npz",
            "tfidf_vectorizer.joblib",
            "svd_model.joblib",
            "rag_store.sqlite",
            "manifest.json",
            "README.md",
            "checksums.sha256",
        ],
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_root / "README.md").write_text(
        """# Managed Humane Connection RAG Index

This directory is generated from `data/rag/source_documents/` by
`python scripts/rebuild_rag.py`. Do not edit generated vector files manually.

The index combines sparse TF-IDF retrieval with dense LSA retrieval. It is rebuilt
as a complete unit whenever a source document, build schema, or chunking setting
changes.
""",
        encoding="utf-8",
    )
    _write_checksums(output_root)

    return BuildResult(
        output_dir=output_root,
        source_files_seen=len(records),
        source_files_indexed=len(indexed_records),
        duplicate_files_skipped=len(records) - len(canonical_records),
        failed_files=len(errors),
        chunks=len(chunks),
        dense_dimensions=int(dense.shape[1]),
        sparse_dimensions=int(tfidf.shape[1]),
        manifest=manifest,
    )
