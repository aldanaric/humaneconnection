"""Generated packet display for Team Diagnostics."""
from __future__ import annotations

import streamlit as st

from services.pdf_export import markdown_to_pdf
import services.team_diagnostics as team_diagnostics


def render(selected_team: str, selected_template: str) -> None:
    saved_output = team_diagnostics.load_saved_output(
        selected_team,
        template_name=selected_template,
    )
    display_output = (
        st.session_state.get(f"last_output_{selected_team}") or saved_output
    )

    if not display_output:
        st.caption("Generate a packet to see output here.")
        return

    col_md, col_pdf = st.columns(2)
    with col_md:
        st.download_button(
            "Download packet markdown",
            data=display_output,
            file_name=f"TeamDiagnostics_{selected_team}.md",
            mime="text/markdown",
        )
    with col_pdf:
        pdf_bytes = markdown_to_pdf(display_output)
        st.download_button(
            "Download packet pdf",
            data=pdf_bytes,
            file_name=f"TeamDiagnostics_{selected_team}.pdf",
            mime="application/pdf",
        )

    st.markdown(display_output)
