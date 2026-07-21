"""Lifecycle management for the locally generated RAG index."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from services import rag_builder


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "data" / "rag" / "source_documents"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "data" / "rag" / "humane_connection_rag"

REQUIRED_INDEX_FILES = {
    "chunks.jsonl",
    "tfidf_vectorizer.joblib",
    "svd_model.joblib",
    "tfidf_matrix.npz",
    "embeddings.npy",
    "manifest.json",
}


@dataclass
class IndexStatus:
    state: str
    message: str
    source_dir: str
    index_dir: str
    index_usable: bool
    source_files: int = 0
    indexed_sources: int = 0
    chunks: int = 0
    built_at_utc: str | None = None
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    config_changed: bool = False
    failed_sources: dict[str, str] = field(default_factory=dict)

    @property
    def needs_rebuild(self) -> bool:
        return self.state in {"missing", "incomplete", "stale", "error"}

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["needs_rebuild"] = self.needs_rebuild
        return data


class RebuildLockError(RuntimeError):
    """Raised when another rebuild currently owns the lock."""


class SubprocessRebuildError(RuntimeError):
    """Raised when an isolated (subprocess) rebuild fails or times out."""


REBUILD_SCRIPT = PROJECT_ROOT / "scripts" / "rebuild_rag.py"


class RebuildLock:
    def __init__(self, lock_path: Path, stale_seconds: int = 3600) -> None:
        self.lock_path = lock_path
        self.stale_seconds = stale_seconds
        self.acquired = False

    def __enter__(self) -> "RebuildLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            age = time.time() - self.lock_path.stat().st_mtime
            if age > self.stale_seconds:
                self.lock_path.unlink(missing_ok=True)
        try:
            descriptor = os.open(
                self.lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError as exc:
            raise RebuildLockError(
                "A knowledge-base rebuild is already running."
            ) from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {"pid": os.getpid(), "started_at": rag_builder.utc_now_iso()}
                )
            )
        self.acquired = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.acquired:
            self.lock_path.unlink(missing_ok=True)


def source_dir() -> Path:
    configured = os.getenv("RAG_SOURCE_DIR", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_SOURCE_DIR


def index_dir() -> Path:
    configured = os.getenv("RAG_BUNDLE_DIR", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_INDEX_DIR


def lock_path() -> Path:
    root = index_dir()
    return root.parent / f".{root.name}.rebuild.lock"


def _read_manifest(root: Path) -> dict[str, Any] | None:
    path = root / "manifest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _snapshot_map(snapshot: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("relative_path")): item for item in snapshot}


def get_status(*, check_sources: bool | None = None) -> IndexStatus:
    sources = source_dir()
    index = index_dir()
    sources.mkdir(parents=True, exist_ok=True)

    if lock_path().exists():
        return IndexStatus(
            state="building",
            message="Knowledge-base rebuild is in progress.",
            source_dir=str(sources),
            index_dir=str(index),
            index_usable=all((index / name).exists() for name in REQUIRED_INDEX_FILES),
        )

    existing_files = {path.name for path in index.iterdir()} if index.exists() else set()
    missing_files = sorted(REQUIRED_INDEX_FILES - existing_files)
    if not index.exists():
        return IndexStatus(
            state="missing",
            message="No generated RAG index exists yet.",
            source_dir=str(sources),
            index_dir=str(index),
            index_usable=False,
            source_files=len(rag_builder.discover_sources(sources)),
        )
    if missing_files:
        return IndexStatus(
            state="incomplete",
            message=f"Generated index is incomplete: missing {', '.join(missing_files)}.",
            source_dir=str(sources),
            index_dir=str(index),
            index_usable=False,
            source_files=len(rag_builder.discover_sources(sources)),
        )

    manifest = _read_manifest(index)
    if manifest is None:
        return IndexStatus(
            state="stale",
            message="Index exists, but its build manifest is missing or invalid.",
            source_dir=str(sources),
            index_dir=str(index),
            index_usable=True,
        )

    if check_sources is None:
        check_sources = os.getenv("RAG_CHECK_FOR_CHANGES", "true").casefold() not in {
            "0",
            "false",
            "no",
            "off",
        }

    failed_sources = dict(manifest.get("failed_sources", {}))
    base = IndexStatus(
        state="error" if failed_sources else "ready",
        message=(
            f"{len(failed_sources)} source document(s) failed during the last rebuild."
            if failed_sources
            else "Knowledge base is current."
        ),
        source_dir=str(sources),
        index_dir=str(index),
        index_usable=True,
        source_files=int(manifest.get("source_files_seen", 0)),
        indexed_sources=int(manifest.get("source_files_indexed", 0)),
        chunks=int(manifest.get("chunks", 0)),
        built_at_utc=manifest.get("created_at_utc"),
        failed_sources=failed_sources,
    )

    config_changed = (
        manifest.get("build_config_fingerprint")
        != rag_builder.build_config_fingerprint()
    )
    base.config_changed = config_changed

    if not check_sources:
        if config_changed:
            base.state = "stale"
            base.message = "Index build settings changed; rebuild recommended."
        return base

    current_snapshot = rag_builder.source_snapshot(sources)
    manifest_snapshot = list(manifest.get("source_snapshot", []))
    current_map = _snapshot_map(current_snapshot)
    manifest_map = _snapshot_map(manifest_snapshot)

    current_names = set(current_map)
    manifest_names = set(manifest_map)
    base.source_files = len(current_snapshot)
    base.added = sorted(current_names - manifest_names)
    base.removed = sorted(manifest_names - current_names)
    base.changed = sorted(
        name
        for name in current_names & manifest_names
        if current_map[name].get("sha256") != manifest_map[name].get("sha256")
    )

    if base.added or base.removed or base.changed or config_changed:
        base.state = "stale"
        reasons: list[str] = []
        if base.added:
            reasons.append(f"{len(base.added)} added")
        if base.changed:
            reasons.append(f"{len(base.changed)} changed")
        if base.removed:
            reasons.append(f"{len(base.removed)} removed")
        if config_changed:
            reasons.append("build settings changed")
        base.message = "Knowledge-base update required: " + ", ".join(reasons) + "."
    return base


def _promote_directory(temp_dir: Path, destination: Path) -> None:
    """Promote a completed index without renaming the bind-mounted directory.

    Docker/WSL bind mounts cannot rename the mount point itself and raise
    ``OSError: [Errno 18] Invalid cross-device link``. To avoid that, this
    function copies the completed build into a staging directory *inside* the
    mounted destination, then swaps the destination's children in place.

    The previous index is retained in an in-mount backup until promotion
    succeeds. If promotion fails, the old index is restored.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)

    staging = destination / ".rebuild-staging"
    backup = destination / ".previous"

    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)

    # Copy across filesystem boundaries into the mounted destination first.
    shutil.copytree(temp_dir, staging)

    missing = sorted(
        name for name in REQUIRED_INDEX_FILES if not (staging / name).exists()
    )
    if missing:
        shutil.rmtree(staging, ignore_errors=True)
        raise RuntimeError(
            "Rebuilt index is incomplete; missing: " + ", ".join(missing)
        )

    backup.mkdir(parents=True, exist_ok=True)
    promoted_names: list[str] = []

    try:
        # Move the active index contents to an in-mount backup. These moves
        # remain on the same filesystem, so os.replace is safe for bind mounts.
        for child in list(destination.iterdir()):
            if child in {staging, backup}:
                continue
            os.replace(child, backup / child.name)

        # Promote the staged files into the active index directory.
        for child in list(staging.iterdir()):
            os.replace(child, destination / child.name)
            promoted_names.append(child.name)

        staging.rmdir()
    except Exception:
        # Remove any partially promoted new files.
        for name in promoted_names:
            promoted = destination / name
            if promoted.is_dir():
                shutil.rmtree(promoted, ignore_errors=True)
            else:
                promoted.unlink(missing_ok=True)

        # Restore the prior valid index.
        if backup.exists():
            for child in list(backup.iterdir()):
                target = destination / child.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink(missing_ok=True)
                os.replace(child, target)

        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
        raise
    else:
        shutil.rmtree(backup, ignore_errors=True)


def rebuild_index() -> rag_builder.BuildResult:
    """Build in a temporary directory and atomically replace the active index."""
    sources = source_dir()
    destination = index_dir()
    sources.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with RebuildLock(lock_path()):
        temp_root = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.build-",
                dir=str(destination.parent),
            )
        )
        try:
            result = rag_builder.build_index(sources, temp_root)
            _promote_directory(temp_root, destination)
            result.output_dir = destination
            return result
        finally:
            # The promotion copies from temp_root, so always remove the
            # temporary build directory after success or failure.
            shutil.rmtree(temp_root, ignore_errors=True)


def rebuild_index_subprocess(timeout: int | None = None) -> dict[str, Any]:
    """Run a full rebuild in an isolated child process.

    Embedding rebuilds (TF-IDF fit + TruncatedSVD) are CPU/memory intensive.
    If something goes wrong in-process (e.g. the OS OOM-killer stepping in,
    or a native BLAS/threading fault), that failure previously took the whole
    Streamlit app down with it, since the build ran on the same process that
    serves the UI. Running the build via `scripts/rebuild_rag.py` in its own
    process means a crash there only ends that child process: this call
    surfaces it as a normal, catchable error instead of killing the app.
    """
    if timeout is None:
        timeout = int(os.getenv("RAG_REBUILD_TIMEOUT_SECONDS", "1800"))

    if not REBUILD_SCRIPT.exists():
        raise SubprocessRebuildError(f"Rebuild script not found at {REBUILD_SCRIPT}.")

    env = os.environ.copy()
    numeric_threads = env.get("RAG_NUMERIC_THREADS", "1").strip() or "1"
    for thread_env in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    ):
        env[thread_env] = numeric_threads

    try:
        completed = subprocess.run(
            [sys.executable, str(REBUILD_SCRIPT), "--json"],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessRebuildError(
            f"Rebuild did not finish within {timeout} seconds and was stopped. "
            "The knowledge base was left untouched; try again, or increase "
            "RAG_REBUILD_TIMEOUT_SECONDS if this keeps happening."
        ) from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        if "RebuildLockError" in stderr or "already running" in stderr:
            raise RebuildLockError("A knowledge-base rebuild is already running.")
        tail = "\n".join(stderr.splitlines()[-20:]) if stderr else completed.stdout[-2000:]
        raise SubprocessRebuildError(
            f"Rebuild process exited with an error (code {completed.returncode}). "
            f"The previous knowledge base was left in place.\n\n{tail}"
        )

    output_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not output_lines:
        raise SubprocessRebuildError(
            "Rebuild process finished but produced no output to confirm success."
        )
    try:
        return json.loads(output_lines[-1])
    except json.JSONDecodeError as exc:
        raise SubprocessRebuildError(
            "Rebuild process finished but its output could not be parsed: "
            f"{output_lines[-1][:2000]}"
        ) from exc


def maybe_auto_rebuild() -> IndexStatus:
    status = get_status()
    auto = os.getenv("RAG_AUTO_REBUILD", "false").casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if auto and status.state in {"missing", "incomplete", "stale"}:
        rebuild_index()
        return get_status()
    return status


def save_uploaded_sources(files: list[tuple[str, bytes]]) -> list[str]:
    """Safely save uploaded files into the managed source directory."""
    root = source_dir()
    root.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for supplied_name, content in files:
        safe_name = Path(supplied_name).name
        if not safe_name or safe_name != supplied_name.replace("\\", "/").split("/")[-1]:
            raise ValueError(f"Unsafe filename: {supplied_name}")
        extension = Path(safe_name).suffix.casefold()
        if extension not in rag_builder.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported document type: {safe_name}")
        destination = root / safe_name
        temporary = root / f".{safe_name}.uploading"
        temporary.write_bytes(content)
        temporary.replace(destination)
        saved.append(safe_name)
    return saved


def delete_sources(relative_paths: list[str]) -> list[str]:
    root = source_dir().resolve()
    deleted: list[str] = []
    for relative_path in relative_paths:
        candidate = (root / relative_path).resolve()
        if root not in candidate.parents:
            raise ValueError(f"Unsafe source path: {relative_path}")
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            deleted.append(relative_path)
    return deleted