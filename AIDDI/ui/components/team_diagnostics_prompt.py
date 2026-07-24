"""Prompt template selection and editing for Team Diagnostics."""
from __future__ import annotations

import streamlit as st

import services.team_diagnostics as team_diagnostics


def render() -> str | None:
    """Render prompt template controls. Returns the selected template name."""
    templates = team_diagnostics.list_prompt_templates()
    if not templates:
        st.error("No prompt templates found.")
        return None

    if "selected_template" not in st.session_state:
        st.session_state.selected_template = templates[0]

    selected_template = st.selectbox(
        "Saved prompt",
        templates,
        index=templates.index(st.session_state.selected_template)
        if st.session_state.selected_template in templates
        else 0,
    )
    st.session_state.selected_template = selected_template

    template = team_diagnostics.load_prompt_template(selected_template)

    with st.expander("Edit prompt template", expanded=False):
        system_prompt_text = st.text_area(
            "System prompt",
            value=template["system_prompt"],
            height=220,
            key=f"system_{selected_template}",
        )
        output_format_text = st.text_area(
            "Output format",
            value=template["output_format"],
            height=220,
            key=f"output_{selected_template}",
        )

        col_save, col_save_as = st.columns(2)
        with col_save:
            if st.button("Save changes", key="save_template"):
                team_diagnostics.save_prompt_template(
                    selected_template,
                    system_prompt_text,
                    output_format_text,
                )
                st.success(f"Saved `{selected_template}`")
                st.rerun()
        with col_save_as:
            with st.form("save_as"):
                new_name = st.text_input(
                    "Save as new template",
                    placeholder="e.g. ignh_facilitator_v2",
                )
                save_as = st.form_submit_button("Save as new")
            if save_as:
                try:
                    saved_name = team_diagnostics.save_prompt_template(
                        new_name,
                        system_prompt_text,
                        output_format_text,
                    )
                    st.session_state.selected_template = saved_name
                    st.success(f"Created `{saved_name}`")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    return selected_template
