"""Team selection and member management for Team Diagnostics."""
from __future__ import annotations

import streamlit as st

import services.team_diagnostics as team_diagnostics


def render() -> str | None:
    """Render team/member controls. Returns the selected team name, if any."""
    with st.expander("➕ Add New Team"):
        with st.form("add_team"):
            team_name_input = st.text_input(
                "Team name",
                placeholder="e.g. IGNH Leadership",
            )
            create_team = st.form_submit_button("Create Team")

    if create_team:
        try:
            folder, existed = team_diagnostics.create_team_folder(team_name_input)
            if existed:
                st.info(f"Team `{folder.name}` already exists.")
            else:
                st.success(f"Team `{folder.name}` created.")
                st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    teams = team_diagnostics.list_teams()
    if not teams:
        st.warning("No teams found. Create a team above to get started.")
        return None

    selected_team = st.selectbox("Select team", teams)

    st.subheader("Team members")
    member_statuses = team_diagnostics.team_member_statuses(selected_team)

    if not member_statuses:
        st.info("No members on this team yet. Add members below.")
    else:
        for status in member_statuses:
            if status["has_personality"]:
                st.success(
                    f"{status['display_name']}: `{status['personality_path'].name}`"
                )
            else:
                st.error(
                    f"{status['display_name']}: Missing personality assessment"
                )

    with st.expander("➕ Add / Update Member"):
        with st.form("add_member"):
            member_name_input = st.text_input(
                "Member name (Last, First)",
                placeholder="e.g. Reyes, Christian",
            )
            personality_upload = st.file_uploader(
                "Personality Assessment",
                type="md",
            )
            add_member = st.form_submit_button("Add/Update Member")

    if add_member:
        try:
            member_folder, _existed = team_diagnostics.create_member_folder(
                selected_team,
                member_name_input,
            )
            last, first = team_diagnostics.split_last_first(member_folder.name)
            destination = member_folder / f"Personality_Assessment_{first}_{last}.md"
            team_diagnostics.save_uploaded_file(personality_upload, destination)

            if personality_upload is None:
                st.warning("Member folder created, but no assessment was uploaded.")
            else:
                st.success(f"Updated `{first} {last}` on `{selected_team}`.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    return selected_team
