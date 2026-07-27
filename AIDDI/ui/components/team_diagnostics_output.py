"""Generated packet display and side-by-side editing for Team Diagnostics."""
from __future__ import annotations

import streamlit as st

from services.pdf_export import markdown_to_pdf
import services.team_diagnostics as team_diagnostics


def render(selected_team: str, selected_template: str) -> None:
    last_key = f"last_output_{selected_team}"
    widget_key = f"td_edit_area_{selected_team}"
    applied_key = f"td_edit_applied_{selected_team}"

    saved_output = team_diagnostics.load_saved_output(
        selected_team,
        template_name=selected_template,
    )
    initial_output = st.session_state.get(last_key) or saved_output

    if not initial_output:
        st.caption("Generate a packet to see output here.")
        return

    # Seed / refresh the editor when content is new (first load or fresh generation).
    source_token = st.session_state.get(last_key) or saved_output
    if widget_key not in st.session_state or st.session_state.get(applied_key) != source_token:
        st.session_state[widget_key] = initial_output
        st.session_state[applied_key] = source_token

    st.caption("Preview on the left, edit on the right. Save to keep your changes.")

    col_preview, col_edit = st.columns(2, gap="large")

    with col_edit:
        st.markdown("**Edit**")
        edited = st.text_area(
            "Edit packet",
            height=700,
            key=widget_key,
            label_visibility="collapsed",
        )

    with col_preview:
        st.markdown("**Preview**")
        with st.container(height=700, border=True):
            st.markdown(edited)

    col_save, col_md, col_pdf = st.columns(3)
    with col_save:
        if st.button("Save edits", type="primary", use_container_width=True):
            saved_path = team_diagnostics.save_team_diagnostics(
                selected_team,
                edited,
                template_name=selected_template,
            )
            st.session_state[last_key] = edited
            st.session_state[applied_key] = edited
            st.success(f"Saved to `{saved_path}`")
    with col_md:
        st.download_button(
            "Download markdown",
            data=edited,
            file_name=f"TeamDiagnostics_{selected_team}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        pdf_bytes = markdown_to_pdf(edited)
        st.download_button(
            "Download pdf",
            data=pdf_bytes,
            file_name=f"TeamDiagnostics_{selected_team}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
