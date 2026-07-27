from pathlib import Path

import streamlit as st

from repositories.account_repository import AccountRepository
from repositories.profile_repository import ProfileRepository
from ui.components import team_diagnostics_team
from ui.components import generate_team_diagnostics
from ui.components import team_diagnostics_output
import services.team_diagnostics as team_diagnostics

logo = Path(__file__).resolve().parents[1] / "static" / "AIDDIlogopendingsquare.png"

st.set_page_config(
    page_title="Team Diagnostics",
    page_icon=logo,
    layout="wide",
)

st.header("Team Diagnostics")
st.write(
    "Build a team from Profiles, add company/team context, and generate a "
    "facilitator packet."
)

# Sidebar is rendered by Home.py
account = st.session_state.get("account")
if account is None:
    st.warning("Log in to use Team Diagnostics.")
    st.stop()

account_repo = AccountRepository()
repo = ProfileRepository(account_repo.get_profiles_root(account))
team_diagnostics.init_prompt_templates()

team_tab, generate_tab, output_tab = st.tabs(
    [
        "Team & members",
        "Generate",
        "Output",
    ]
)

with team_tab:
    selected_team = team_diagnostics_team.render(repo)

if not selected_team:
    st.info("Create or select a team in the **Team & members** tab to continue.")
    st.stop()

with generate_tab:
    selected_template = generate_team_diagnostics.render(selected_team, repo)

with output_tab:
    team_diagnostics_output.render(selected_team, selected_template)
