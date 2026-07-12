"""Retrieval-Augmented Generation over the locally built Humane Connection index.

This module queries the hybrid TF-IDF + LSA index produced by
``services/rag_builder.py`` (see ``services/rag_index_manager.py`` for where the
index lives and how it is rebuilt). It intentionally does not call any external
embeddings API: the index and the query embedding both come from the same local
scikit-learn artifacts (``tfidf_vectorizer.joblib`` / ``svd_model.joblib``), so
retrieval stays consistent with how the corpus vectors were produced.

If the knowledge base has never been built, or is stale relative to the source
documents, the retrieval functions below raise a clear, actionable error instead
of silently returning nothing.
"""
from __future__ import annotations

import io
import json
import os
import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy import sparse

from services import rag_builder, rag_index_manager

# Hybrid weighting, matches the value recorded in each build's manifest.json
# ("retrieval_default": "hybrid cosine: 0.65 sparse TF-IDF + 0.35 dense LSA").
SPARSE_WEIGHT = 0.65
DENSE_WEIGHT = 0.35

_lock = threading.Lock()
_cache: dict[str, Any] = {}


class RAGNotReadyError(RuntimeError):
    """Raised when the knowledge base index is missing, incomplete, or stale."""


def _load_index() -> dict[str, Any]:
    """Load (and cache) the vectorizer, SVD model, corpus vectors, and chunks."""
    index_dir = rag_index_manager.index_dir()
    status = rag_index_manager.get_status()

    if status.state in {"missing", "incomplete", "building"}:
        raise RAGNotReadyError(
            f"The Humane Connection knowledge base isn't ready yet ({status.message}). "
            "Open the Knowledge Base page and click 'Rebuild knowledge base', or run "
            "`python scripts/rebuild_rag.py`."
        )

    with _lock:
        cached = _cache.get("index_dir")
        cached_built_at = _cache.get("built_at_utc")
        if cached == str(index_dir) and cached_built_at == status.built_at_utc:
            return _cache

        vectorizer = joblib.load(index_dir / "tfidf_vectorizer.joblib")
        svd_model = joblib.load(index_dir / "svd_model.joblib")
        tfidf_matrix = sparse.load_npz(index_dir / "tfidf_matrix.npz")
        dense_matrix = np.load(index_dir / "embeddings.npy")

        chunks: list[dict[str, Any]] = []
        with open(index_dir / "chunks.jsonl", "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    chunks.append(json.loads(line))

        if not (len(chunks) == tfidf_matrix.shape[0] == dense_matrix.shape[0]):
            raise RAGNotReadyError(
                "The knowledge base index looks corrupted (row counts don't match "
                "between chunks.jsonl, tfidf_matrix.npz, and embeddings.npy). "
                "Rebuild it from the Knowledge Base page."
            )

        _cache.clear()
        _cache.update(
            {
                "index_dir": str(index_dir),
                "built_at_utc": status.built_at_utc,
                "vectorizer": vectorizer,
                "svd_model": svd_model,
                "tfidf_matrix": tfidf_matrix,
                "dense_matrix": dense_matrix,
                "chunks": chunks,
            }
        )
        return _cache


def _location_label(chunk: dict[str, Any]) -> str:
    page_start, page_end = chunk.get("page_start"), chunk.get("page_end")
    if page_start is not None:
        if page_end is not None and page_end != page_start:
            return f"pages {page_start}-{page_end}"
        return f"page {page_start}"
    para_start, para_end = chunk.get("paragraph_start"), chunk.get("paragraph_end")
    if para_start is not None:
        if para_end is not None and para_end != para_start:
            return f"paragraphs {para_start}-{para_end}"
        return f"paragraph {para_start}"
    return "location not recorded"


def retrieve_context(query: str, top_k: int = 3) -> dict[str, Any]:
    """Retrieve the most relevant Humane Connection chunks for ``query``.

    Uses a hybrid of sparse TF-IDF cosine similarity and dense LSA cosine
    similarity, matching the retrieval method the index was built and
    validated with.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    index = _load_index()
    vectorizer = index["vectorizer"]
    svd_model = index["svd_model"]
    tfidf_matrix = index["tfidf_matrix"]
    dense_matrix = index["dense_matrix"]
    chunks = index["chunks"]

    requested_top_k = max(1, min(int(top_k), len(chunks)))

    query_tfidf = vectorizer.transform([query])  # already L2-normalized (norm="l2" default)
    sparse_scores = np.asarray(tfidf_matrix.dot(query_tfidf.T).todense()).ravel()

    query_dense = svd_model.transform(query_tfidf).astype(np.float32)
    query_norm = np.linalg.norm(query_dense, axis=1, keepdims=True)
    query_norm[query_norm == 0] = 1.0
    query_dense = query_dense / query_norm
    dense_scores = dense_matrix.dot(query_dense.reshape(-1))

    hybrid_scores = SPARSE_WEIGHT * sparse_scores + DENSE_WEIGHT * dense_scores

    top_indices = np.argsort(hybrid_scores)[::-1][:requested_top_k]

    top_records = []
    for idx in top_indices:
        chunk = chunks[int(idx)]
        top_records.append(
            {
                "document_name": chunk.get("source"),
                "source": chunk.get("source"),
                "section": chunk.get("section"),
                "location": _location_label(chunk),
                "page_number": chunk.get("page_start"),
                "context": chunk.get("text", ""),
                "text": chunk.get("text", ""),
                "score": float(hybrid_scores[int(idx)]),
            }
        )

    if not top_records:
        raise RuntimeError("No relevant passages were found in the knowledge base.")

    best_record = top_records[0]
    combined_context = "\n\n---\n\n".join(
        f"Source: {record['document_name']}, {record['location']}\n{record['context']}"
        for record in top_records
    )

    return {
        "context": best_record["context"],
        "page_number": best_record["page_number"],
        "document_name": best_record["document_name"],
        "combined_context": combined_context,
        "records": top_records,
    }


async def ask_book(query: str, return_image: bool = False) -> dict[str, Any]:
    """Answer a question using the local Humane Connection knowledge base."""
    retrieved = retrieve_context(query, top_k=3)
    prompt = (
        "You are an expert assistant for Humane Connection.\n"
        "Answer the user's question using the retrieved Humane Connection "
        "excerpts below. Do not claim that unsupported details are in the source.\n\n"
        f"Retrieved excerpts:\n{retrieved['combined_context']}\n\n"
        f"User question: {query}\n\n"
        "Provide a clear, practical answer grounded in the excerpts."
    )

    from services.llm import converse_sync

    answer, _ = converse_sync(prompt=prompt, messages=[])
    result = {
        "answer": answer,
        "page_number": retrieved["page_number"],
        "context": retrieved["context"],
        "document_name": retrieved["document_name"],
        "records": retrieved["records"],
    }

    if return_image:
        result["image_data"] = b""
        document_name = retrieved.get("document_name")
        page_number = retrieved.get("page_number")
        if document_name and str(document_name).lower().endswith(".pdf") and page_number:
            pdf_path = rag_index_manager.source_dir() / document_name
            try:
                result["image_data"] = _extract_page_as_image(pdf_path, page_number)
            except Exception as exc:
                print(f"RAG image generation skipped: {exc}")

    return result


def _extract_page_as_image(pdf_path: Path, page_number: int) -> bytes:
    """Convert a specific PDF page to PNG image bytes for the evidence panel."""
    from pdf2image import convert_from_path

    try:
        images = convert_from_path(
            str(pdf_path), first_page=page_number, last_page=page_number, dpi=150
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to render PDF page image. Make sure Poppler is installed and "
            f"available in PATH. Original error: {exc}"
        )

    if not images:
        return b""
    buffer = io.BytesIO()
    images[0].save(buffer, format="PNG")
    return buffer.getvalue()
