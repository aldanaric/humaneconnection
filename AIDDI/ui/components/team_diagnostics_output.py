"""Generated packet display and side-by-side editing for Team Diagnostics."""
from __future__ import annotations

import streamlit as st

from models.account import Account
from models.team_diagnostic_report import TeamDiagnosticReport
from services.pdf_export import markdown_to_pdf
import services.team_diagnostics as team_diagnostics


def _report_id_key(team_name: str) -> str:
    return f"td_current_report_id_{team_name}"


def _content_key(team_name: str) -> str:
    return f"last_output_{team_name}"


def _widget_key(team_name: str) -> str:
    return f"td_edit_area_{team_name}"


def _applied_key(team_name: str) -> str:
    return f"td_edit_applied_{team_name}"


def _title_key(team_name: str) -> str:
    return f"td_report_title_{team_name}"


def _pending_key(team_name: str) -> str:
    return f"td_pending_report_{team_name}"


def set_current_report(team_name: str, report: TeamDiagnosticReport) -> None:
    """Queue a report for the Output tab (safe before/after widgets via pending seed)."""
    st.session_state[_report_id_key(team_name)] = report.id
    st.session_state[_content_key(team_name)] = report.content
    st.session_state[_pending_key(team_name)] = {
        "title": report.title,
        "content": report.content,
    }


def _apply_pending(team_name: str) -> None:
    """Apply queued title/content before widgets are created this run."""
    pending = st.session_state.pop(_pending_key(team_name), None)
    if not pending:
        return
    st.session_state[_title_key(team_name)] = pending["title"]
    st.session_state[_widget_key(team_name)] = pending["content"]
    st.session_state[_applied_key(team_name)] = pending["content"]
    st.session_state[_content_key(team_name)] = pending["content"]


def render(account: Account, selected_team: str, selected_template: str) -> None:
    report_id_key = _report_id_key(selected_team)
    content_key = _content_key(selected_team)
    widget_key = _widget_key(selected_team)
    applied_key = _applied_key(selected_team)
    title_key = _title_key(selected_team)

    _apply_pending(selected_team)

    current_report: TeamDiagnosticReport | None = None
    current_id = st.session_state.get(report_id_key)
    if current_id:
        current_report = team_diagnostics.get_saved_report(account, current_id)

    if current_report is None:
        current_report = team_diagnostics.load_latest_report(
            account,
            selected_team,
            template_name=selected_template,
        )
        if current_report is not None:
            st.session_state[report_id_key] = current_report.id
            st.session_state[content_key] = current_report.content
            if title_key not in st.session_state:
                st.session_state[title_key] = current_report.title
            if widget_key not in st.session_state:
                st.session_state[widget_key] = current_report.content
                st.session_state[applied_key] = current_report.content

    if current_report is None and not st.session_state.get(content_key):
        st.caption("Generate a packet to see output here.")
        return

    initial_output = st.session_state.get(content_key) or (
        current_report.content if current_report else ""
    )
    if not initial_output:
        st.caption("Generate a packet to see output here.")
        return

    source_token = st.session_state.get(content_key) or initial_output
    if widget_key not in st.session_state or st.session_state.get(applied_key) != source_token:
        st.session_state[widget_key] = initial_output
        st.session_state[applied_key] = source_token

    if title_key not in st.session_state:
        st.session_state[title_key] = (
            current_report.title
            if current_report
            else f"Team Diagnostics — {selected_team}"
        )

    report_title = st.text_input(
        "Report name",
        key=title_key,
        help="Rename this saved output. Click Save edits to keep the new name.",
    )

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
            try:
                if current_report is not None:
                    report = team_diagnostics.update_team_diagnostics(
                        account,
                        current_report.id,
                        content=edited,
                        title=report_title,
                    )
                else:
                    report = team_diagnostics.save_team_diagnostics(
                        account,
                        selected_team,
                        edited,
                        template_name=selected_template,
                        title=report_title,
                    )
                set_current_report(selected_team, report)
                st.success(f"Saved report `{report.title}`.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with col_md:
        st.download_button(
            "Download markdown",
            data=edited,
            file_name=f"{report_title or selected_team}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        pdf_bytes = markdown_to_pdf(edited)
        st.download_button(
            "Download pdf",
            data=pdf_bytes,
            file_name=f"{report_title or selected_team}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
