"""Team selection, company/team context, and profile-linked members."""
from __future__ import annotations

import streamlit as st

from models.account import Account
from models.document_type import DocumentType
from repositories.profile_repository import ProfileRepository
from ui.components.create_profile_dialog import open_create_profile_dialog
from ui.components import profile_picker
import services.team_diagnostics as team_diagnostics


@st.dialog("Edit team member", width="large")
def _edit_member_dialog(profile_id: str, repo: ProfileRepository) -> None:
    """Popup editor for a linked profile's personality and job functions."""
    try:
        profile = repo.get_profile(profile_id)
    except FileNotFoundError:
        st.error("Profile not found.")
        return

    st.subheader(profile.display_name)
    if profile.company_name:
        st.caption(profile.company_name)

    st.markdown("**Personality assessment**")
    personality = repo.load_document(profile, DocumentType.PERSONALITY)
    personality_col, personality_upload_col = st.columns(2)
    with personality_col:
        edited_personality = st.text_area(
            "Personality assessment",
            value=personality,
            height=280,
            key=f"dialog_personality_{profile.id}",
            label_visibility="collapsed",
        )
    with personality_upload_col:
        personality_upload = st.file_uploader(
            "Upload replacement",
            type=["md", "pdf"],
            key=f"dialog_personality_upload_{profile.id}",
        )
        if personality_upload is not None:
            repo.upload_document(profile, DocumentType.PERSONALITY, personality_upload)
            st.success("Personality assessment uploaded.")
            st.rerun()

    st.markdown("**Job functions**")
    job_functions = repo.load_document(profile, DocumentType.JOB_FUNCTIONS)
    job_col, job_upload_col = st.columns(2)
    with job_col:
        edited_jobs = st.text_area(
            "Job functions",
            value=job_functions,
            height=280,
            key=f"dialog_jobs_{profile.id}",
            label_visibility="collapsed",
        )
    with job_upload_col:
        job_upload = st.file_uploader(
            "Upload replacement",
            type=["md", "pdf"],
            key=f"dialog_jobs_upload_{profile.id}",
        )
        if job_upload is not None:
            repo.upload_document(profile, DocumentType.JOB_FUNCTIONS, job_upload)
            st.success("Job functions uploaded.")
            st.rerun()

    col_save, col_close = st.columns(2)
    with col_save:
        if st.button("Save changes", type="primary", use_container_width=True):
            repo.save_document(profile, DocumentType.PERSONALITY, edited_personality)
            repo.save_document(profile, DocumentType.JOB_FUNCTIONS, edited_jobs)
            st.success(f"Saved updates for {profile.display_name}.")
            st.rerun()
    with col_close:
        if st.button("Close", use_container_width=True):
            st.rerun()


def render(account: Account, repo: ProfileRepository) -> str | None:
    """Render team/member controls. Returns the selected team name, if any."""
    with st.expander("➕ Add New Team"):
        with st.form("add_team"):
            team_name_input = st.text_input(
                "Team name",
                placeholder="e.g. IGNH Leadership",
            )
            company_info_input = st.text_area(
                "Company / organization info (optional)",
                placeholder="Industry, size, mission, operating context…",
                height=100,
            )
            team_info_input = st.text_area(
                "Team context (optional)",
                placeholder="Team purpose, working norms, current challenges…",
                height=100,
            )
            create_team = st.form_submit_button("Create Team")

    if create_team:
        try:
            folder_name, existed = team_diagnostics.create_team(
                account,
                team_name_input,
                company_info=company_info_input,
                team_info=team_info_input,
            )
            if existed:
                st.info(f"Team `{folder_name}` already exists.")
            else:
                st.success(f"Team `{folder_name}` created.")
                st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Could not create team: {exc}")

    try:
        teams = team_diagnostics.list_teams(account)
    except Exception as exc:
        st.error(
            "Could not load teams from the database. "
            "Start Postgres (`docker compose up -d postgres`) and run "
            "`uv run python scripts/db_migrate.py`.\n\n"
            f"Details: {exc}"
        )
        return None

    if not teams:
        st.warning("No teams found. Create a team above to get started.")
        return None

    team_records = {
        team.name: team for team in team_diagnostics.list_team_records(account)
    }
    selected_team = st.selectbox(
        "Select team",
        teams,
        format_func=lambda name: (
            team_records[name].display_name
            if name in team_records and team_records[name].display_name
            else name
        ),
    )
    config = team_diagnostics.load_team_config(account, selected_team)

    st.subheader("Company & team context")
    display_name = st.text_input(
        "Display name",
        value=config.get("display_name") or selected_team,
        key=f"team_display_name_{selected_team}",
    )
    company_info = st.text_area(
        "Company / organization info",
        value=config.get("company_info", ""),
        height=120,
        key=f"company_info_{selected_team}",
        help="Shared organizational context used when generating the packet.",
    )
    team_info = st.text_area(
        "Team context",
        value=config.get("team_info", ""),
        height=120,
        key=f"team_info_{selected_team}",
        help="Team-specific notes such as purpose, norms, or current challenges.",
    )
    if st.button("Save team context", key=f"save_team_context_{selected_team}"):
        team_diagnostics.update_team_context(
            account,
            selected_team,
            company_info=company_info,
            team_info=team_info,
            display_name=display_name,
        )
        st.success("Team context saved.")
        st.rerun()

    st.subheader("Team members")
    st.caption(
        "Members are linked to Profiles so personality assessments and job "
        "functions stay consistent across Growth Plan and Team Diagnostics. "
        "Use Edit to update a person's inputs here."
    )

    member_statuses = team_diagnostics.team_member_statuses(
        account,
        selected_team,
        repo,
    )
    if not member_statuses:
        st.info("No members on this team yet. Add profiles below.")
    else:
        for status in member_statuses:
            profile_id = str(status["profile_id"])
            label = status["display_name"]
            with st.container(border=True):
                col_status, col_edit, col_remove = st.columns([4, 1, 1])
                with col_status:
                    if status.get("missing_profile"):
                        st.error(f"{label}: profile not found")
                    elif status.get("is_ready"):
                        st.success(f"{label}: personality ✓ · job functions ✓")
                    else:
                        missing = []
                        if not status.get("has_personality"):
                            missing.append("personality")
                        if not status.get("has_job_functions"):
                            missing.append("job functions")
                        st.warning(f"{label}: missing {', '.join(missing)}")

                with col_edit:
                    edit_disabled = bool(status.get("missing_profile"))
                    if st.button(
                        "Edit",
                        key=f"edit_member_{selected_team}_{profile_id}",
                        use_container_width=True,
                        disabled=edit_disabled,
                    ):
                        _edit_member_dialog(profile_id, repo)

                with col_remove:
                    if st.button(
                        "Remove",
                        key=f"remove_member_{selected_team}_{profile_id}",
                        use_container_width=True,
                    ):
                        team_diagnostics.remove_member_profile(
                            account,
                            selected_team,
                            profile_id,
                        )
                        st.rerun()

    profiles = repo.list_profiles()
    member_ids = set(team_diagnostics.list_member_profile_ids(account, selected_team))
    available = [profile for profile in profiles if profile.id not in member_ids]

    with st.expander("➕ Add member from Profiles"):
        if st.button(
            "Create new profile",
            key=f"create_profile_btn_{selected_team}",
        ):
            open_create_profile_dialog(repo)

        if not available:
            st.info(
                "No available profiles to add. Create a new profile above, "
                "or add one from the Profiles / Growth Plan pages."
            )
        else:
            companies = profile_picker.list_companies(available)
            selected_company = st.selectbox(
                "Company",
                [profile_picker.SELECT_COMPANY, *companies],
                key=f"add_member_company_{selected_team}",
            )

            if selected_company == profile_picker.SELECT_COMPANY:
                st.caption("Choose a company to see available employees.")
            else:
                company_profiles = profile_picker.profiles_for_company(
                    available,
                    selected_company,
                )
                if not company_profiles:
                    st.info("No available profiles left for that company.")
                else:
                    selected_profile = st.selectbox(
                        "Employee",
                        company_profiles,
                        format_func=lambda profile: profile.display_name,
                        key=f"add_profile_select_{selected_team}_{selected_company}",
                    )
                    if st.button(
                        "Add to team",
                        key=f"add_profile_btn_{selected_team}",
                    ):
                        try:
                            team_diagnostics.add_member_profile(
                                account,
                                selected_team,
                                selected_profile,
                            )
                            st.success(f"Added {selected_profile.display_name}.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(f"Could not add member: {exc}")

    return selected_team
