"""Reusable Streamlit rendering for RAG retrieval evidence."""
from __future__ import annotations

from typing import Any, Sequence

import streamlit as st


def render(
    sources: Sequence[dict[str, Any]],
    *,
    title: str = "Retrieved knowledge sources",
    expanded: bool = False,
) -> None:
    if not sources:
        st.caption("No sufficiently relevant knowledge-base passages were retrieved.")
        return

    with st.expander(f"{title} ({len(sources)})", expanded=expanded):
        for number, source in enumerate(sources, start=1):
            source_name = source.get("source", "Unknown source")
            location = source.get("location", "location not recorded")
            section = source.get("section")
            score = float(source.get("score", 0.0))

            st.markdown(f"**[RAG {number}] {source_name}** — {location}")
            details = []
            if section:
                details.append(f"Section: {section}")
            details.append(f"retrieval score: {score:.3f}")
            st.caption(" · ".join(details))
            if source.get("text"):
                st.write(source["text"])
            if number < len(sources):
                st.divider()
