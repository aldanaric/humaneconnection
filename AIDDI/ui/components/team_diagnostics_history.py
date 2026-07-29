"""History of saved Team Diagnostics reports for a team."""
from __future__ import annotations

import streamlit as st

from models.account import Account
from services.pdf_export import markdown_to_pdf
import services.team_diagnostics as team_diagnostics


def _dialog_version_key(report_id: str) -> str:
    return f"history_dialog_ver_{report_id}"


def _clear_output_session_if_current(team_name: str, report_id: str) -> None:
    """If Output tab was pointing at this report, clear that selection."""
    current_key = f"td_current_report_id_{team_name}"
    if st.session_state.get(current_key) == report_id:
        for key in (
            current_key,
            f"last_output_{team_name}",
            f"td_edit_area_{team_name}",
            f"td_edit_applied_{team_name}",
            f"td_report_title_{team_name}",
            f"td_pending_report_{team_name}",
        ):
            st.session_state.pop(key, None)


def _delete_report(account: Account, team_name: str, report_id: str, title: str) -> None:
    team_diagnostics.delete_team_diagnostics(account, report_id)
    _clear_output_session_if_current(team_name, report_id)
    st.session_state.pop(_dialog_version_key(report_id), None)
    st.success(f"Deleted `{title}`.")
    st.rerun()


@st.dialog("Saved report", width="large")
def _open_report_dialog(account: Account, team_name: str, report_id: str) -> None:
    """Large popup mirroring the Output tab: rename, preview/edit, save, download."""
    report = team_diagnostics.get_saved_report(account, report_id)
    if report is None:
        st.error("Report not found.")
        return

    # Versioned keys: never overwrite an existing widget key (Streamlit forbids it
    # once the widget/fragment has been instantiated).
    version = st.session_state.get(_dialog_version_key(report_id), 0)
    title_key = f"history_dialog_title_{report_id}_{version}"
    edit_key = f"history_dialog_edit_{report_id}_{version}"

    if title_key not in st.session_state:
        st.session_state[title_key] = report.title
    if edit_key not in st.session_state:
        st.session_state[edit_key] = report.content

    updated = (
        report.updated_at.strftime("%Y-%m-%d %H:%M")
        if report.updated_at
        else "unknown"
    )
    st.caption(
        f"Audience: {report.audience} · Template: {report.prompt_template_name} · "
        f"Updated {updated}"
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
            height=500,
            key=edit_key,
            label_visibility="collapsed",
        )
    with col_preview:
        st.markdown("**Preview**")
        with st.container(height=500, border=True):
            st.markdown(edited)

    col_save, col_md, col_pdf, col_delete, col_close = st.columns(5)
    with col_save:
        if st.button("Save edits", type="primary", use_container_width=True):
            try:
                updated_report = team_diagnostics.update_team_diagnostics(
                    account,
                    report.id,
                    content=edited,
                    title=report_title,
                )
                st.success(f"Saved report `{updated_report.title}`.")
            except ValueError as exc:
                st.error(str(exc))
    with col_md:
        st.download_button(
            "Download markdown",
            data=edited,
            file_name=f"{report_title or 'team_diagnostics'}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        pdf_bytes = markdown_to_pdf(edited)
        st.download_button(
            "Download pdf",
            data=pdf_bytes,
            file_name=f"{report_title or 'team_diagnostics'}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_delete:
        if st.button("Delete", use_container_width=True):
            st.session_state[f"confirm_delete_dialog_{report_id}"] = True
    with col_close:
        if st.button("Close", use_container_width=True):
            st.rerun()

    if st.session_state.get(f"confirm_delete_dialog_{report_id}"):
        st.warning(f"Delete `{report.title}`? This cannot be undone.")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button(
                "Yes, delete",
                type="primary",
                key=f"confirm_delete_yes_{report_id}",
                use_container_width=True,
            ):
                st.session_state.pop(f"confirm_delete_dialog_{report_id}", None)
                _delete_report(account, team_name, report.id, report.title)
        with cancel_col:
            if st.button(
                "Cancel",
                key=f"confirm_delete_no_{report_id}",
                use_container_width=True,
            ):
                st.session_state.pop(f"confirm_delete_dialog_{report_id}", None)
                st.rerun()


def render(account: Account, selected_team: str) -> None:
    reports = team_diagnostics.list_saved_outputs(account, selected_team)

    if not reports:
        st.info(
            "No saved reports for this team yet. Generate a packet on the "
            "**Generate** tab to create history."
        )
        return

    st.caption(
        "Open a past report to review or edit, or delete reports you no longer need."
    )

    for report in reports:
        updated = (
            report.updated_at.strftime("%Y-%m-%d %H:%M")
            if report.updated_at
            else "unknown"
        )
        with st.container(border=True):
            col_info, col_open, col_delete = st.columns([4, 1, 1])
            with col_info:
                st.markdown(f"**{report.title}**")
                st.caption(
                    f"Updated {updated} · Audience: {report.audience} · "
                    f"Template: {report.prompt_template_name}"
                )
            with col_open:
                if st.button(
                    "Open",
                    key=f"open_report_{selected_team}_{report.id}",
                    use_container_width=True,
                ):
                    ver_key = _dialog_version_key(report.id)
                    st.session_state[ver_key] = st.session_state.get(ver_key, 0) + 1
                    _open_report_dialog(account, selected_team, report.id)
            with col_delete:
                if st.button(
                    "Delete",
                    key=f"delete_report_{selected_team}_{report.id}",
                    use_container_width=True,
                ):
                    st.session_state[f"confirm_delete_list_{report.id}"] = True

            if st.session_state.get(f"confirm_delete_list_{report.id}"):
                st.warning(f"Delete `{report.title}`? This cannot be undone.")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button(
                        "Yes, delete",
                        type="primary",
                        key=f"confirm_delete_list_yes_{report.id}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(f"confirm_delete_list_{report.id}", None)
                        _delete_report(
                            account,
                            selected_team,
                            report.id,
                            report.title,
                        )
                with cancel_col:
                    if st.button(
                        "Cancel",
                        key=f"confirm_delete_list_no_{report.id}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(f"confirm_delete_list_{report.id}", None)
                        st.rerun()
