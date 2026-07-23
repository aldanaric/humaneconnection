import json
from pathlib import Path

import streamlit as st

from ui.components import sidebar
from services import rag_index_manager

logo = Path(__file__).resolve().parents[1] / "static" / "AIDDIlogopendingsquare.png"

st.set_page_config(
    page_title="Knowledge Base",
    page_icon=logo,
    layout="wide",
)

st.header("Knowledge Base")
st.write(
    "Manage the Humane Connection source documents and the local retrieval "
    "index (TF-IDF + LSA) used by Quick Chat and Growth Plan. This page "
    "also shows whether the index still matches the source documents on "
    "disk, and lets you rebuild it when it doesn't."
)

#sidebar.show()

status = rag_index_manager.get_status()

STATE_DISPLAY = {
    "ready": ("success", "✅ Ready", "The index matches the current source documents."),
    "missing": ("error", "⚠️ Not built yet", "Build the index before Quick Chat or Growth Plan can use it."),
    "incomplete": ("error", "⚠️ Incomplete", "Some required index files are missing."),
    "stale": ("warning", "🟡 Needs a rebuild", "Source documents have changed since the index was last built."),
    "building": ("info", "⏳ Rebuild in progress", "Another rebuild is currently running."),
    "error": ("error", "❌ Build had errors", "One or more source documents failed to index."),
}
kind, title, subtitle = STATE_DISPLAY.get(status.state, ("info", status.state, ""))

banner = {"success": st.success, "warning": st.warning, "error": st.error, "info": st.info}[kind]
banner(f"**{title}** — {subtitle}")
st.caption(status.message)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Source files", status.source_files)
col2.metric("Indexed sources", status.indexed_sources)
col3.metric("Chunks", status.chunks)
col4.metric("Last built (UTC)", status.built_at_utc or "never")

if status.failed_sources:
    with st.expander("Sources that failed to index", expanded=True):
        for name, error in status.failed_sources.items():
            st.error(f"{name}: {error}")

# --- Rebuild ---------------------------------------------------------------

st.divider()
st.subheader("Rebuild")
st.caption(
    "Rebuilding runs in its own isolated process, separate from the app "
    "server. If the build fails or runs out of memory, only that process "
    "stops — this app keeps running and the previous, working index stays "
    "in place until a rebuild succeeds."
)

rebuild_disabled = status.state == "building"
if st.button(
    "Rebuild knowledge base now",
    type="primary",
    disabled=rebuild_disabled,
    key="kb_rebuild_button",
    help=(
        "Re-extracts, re-chunks, and re-embeds every source document. Runs in "
        "an isolated process so a build failure can't crash this app."
    ),
):
    with st.spinner("Rebuilding knowledge base... this can take a minute."):
        try:
            summary = rag_index_manager.rebuild_index_subprocess()
            st.success(
                f"Rebuilt index: {summary.get('chunks')} chunks from "
                f"{summary.get('source_files_indexed')} source documents "
                f"({summary.get('failed_files', 0)} failed)."
            )
            st.rerun()
        except rag_index_manager.RebuildLockError as exc:
            st.warning(str(exc))
        except rag_index_manager.SubprocessRebuildError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Rebuild failed: {exc}")

# --- What changed since the last build --------------------------------------

st.divider()
st.subheader("What changed since the last build")

if not (status.added or status.changed or status.removed or status.config_changed):
    st.caption("No file changes detected since the last build.")
else:
    change_col1, change_col2, change_col3 = st.columns(3)
    with change_col1:
        st.markdown("**Added**")
        st.write("\n".join(f"- {name}" for name in status.added) or "_none_")
    with change_col2:
        st.markdown("**Changed**")
        st.write("\n".join(f"- {name}" for name in status.changed) or "_none_")
    with change_col3:
        st.markdown("**Removed**")
        st.write("\n".join(f"- {name}" for name in status.removed) or "_none_")
    if status.config_changed:
        st.info(
            "Build settings (chunking, vectorizer, etc.) changed since the last "
            "build, independent of the source files themselves."
        )

# --- Source documents --------------------------------------------------------

st.divider()
st.subheader("Source documents")
st.caption(f"Managed folder: `{status.source_dir}`")

uploaded_files = st.file_uploader(
    "Add source documents (.pdf, .docx, .txt, .md)",
    type=["pdf", "docx", "txt", "md"],
    accept_multiple_files=True,
)
if uploaded_files and st.button("Save uploaded documents"):
    try:
        saved = rag_index_manager.save_uploaded_sources(
            [(f.name, f.getvalue()) for f in uploaded_files]
        )
        st.success(f"Saved: {', '.join(saved)}. Rebuild the knowledge base to include them.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

source_dir = rag_index_manager.source_dir()
existing = sorted(p.name for p in source_dir.glob("*") if p.is_file())
if existing:
    to_delete = st.multiselect("Existing source documents", existing)
    if to_delete and st.button("Delete selected documents", type="secondary"):
        deleted = rag_index_manager.delete_sources(to_delete)
        st.success(f"Deleted: {', '.join(deleted)}. Rebuild the knowledge base to apply this.")
        st.rerun()
else:
    st.caption("No source documents found yet.")

# --- Build details -----------------------------------------------------------

st.divider()
with st.expander("Build details (from the last successful build manifest)"):
    manifest_path = rag_index_manager.index_dir() / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            details = {
                "index_method": manifest.get("index_method"),
                "dense_dimensions": manifest.get("dense_dimensions"),
                "sparse_dimensions": manifest.get("sparse_dimensions"),
                "retrieval_default": manifest.get("retrieval_default"),
                "created_at_utc": manifest.get("created_at_utc"),
                "build_config_fingerprint": manifest.get("build_config_fingerprint"),
                "source_snapshot_fingerprint": manifest.get("source_snapshot_fingerprint"),
            }
            st.json(details)
        except (OSError, json.JSONDecodeError) as exc:
            st.caption(f"Could not read manifest.json: {exc}")
    else:
        st.caption("No manifest.json found yet — the index hasn't been built.")