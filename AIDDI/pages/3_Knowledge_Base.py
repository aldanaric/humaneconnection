from pathlib import Path

import streamlit as st

from ui.components import sidebar
from services import rag_index_manager

logo = Path(__file__).resolve().parent / "static" / "AIDDIlogopendingquare.png"

st.set_page_config(
    page_title="Knowledge Base",
    page_icon=logo,
    layout="wide",
)

st.header("Knowledge Base")
st.write(
    "Manage the Humane Connection source documents and the local retrieval "
    "index (TF-IDF + LSA) used by Quick Chat and Growth Plan."
)

#sidebar.show()

status = rag_index_manager.get_status()

STATE_LABELS = {
    "ready": ("✅", "Ready"),
    "missing": ("⚠️", "Not built yet"),
    "incomplete": ("⚠️", "Incomplete"),
    "stale": ("⚠️", "Needs a rebuild"),
    "building": ("⏳", "Rebuild in progress"),
    "error": ("❌", "Build had errors"),
}
icon, label = STATE_LABELS.get(status.state, ("ℹ️", status.state))

st.subheader(f"{icon} {label}")
st.caption(status.message)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Source files", status.source_files)
col2.metric("Indexed sources", status.indexed_sources)
col3.metric("Chunks", status.chunks)
col4.metric("Last built", status.built_at_utc or "never")

if status.added:
    st.info(f"New since last build: {', '.join(status.added)}")
if status.changed:
    st.info(f"Changed since last build: {', '.join(status.changed)}")
if status.removed:
    st.info(f"Removed since last build: {', '.join(status.removed)}")
if status.failed_sources:
    with st.expander("Sources that failed to index", expanded=True):
        for name, error in status.failed_sources.items():
            st.error(f"{name}: {error}")

rebuild_disabled = status.state == "building"
if st.button(
    "Rebuild knowledge base now",
    type="primary",
    disabled=rebuild_disabled,
    help="Re-extracts, re-chunks, and re-embeds every source document.",
):
    with st.spinner("Rebuilding knowledge base... this can take a minute."):
        try:
            result = rag_index_manager.rebuild_index()
            st.success(
                f"Rebuilt index: {result.chunks} chunks from "
                f"{result.source_files_indexed} source documents."
            )
            st.rerun()
        except rag_index_manager.RebuildLockError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"Rebuild failed: {exc}")

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
