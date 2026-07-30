from pathlib import Path

import streamlit as st

from repositories.profile_repository import ProfileRepository
from ui.components import team_diagnostics_team
from ui.components import generate_team_diagnostics
from ui.components import team_diagnostics_output
from ui.components import team_diagnostics_history
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

repo = ProfileRepository(account.id)
team_diagnostics.init_prompt_templates()

team_tab, generate_tab, output_tab, history_tab = st.tabs(
    [
        "Team & members",
        "Generate",
        "Output",
        "History",
    ]
)

with team_tab:
    selected_team = team_diagnostics_team.render(account, repo)

if not selected_team:
    st.info("Create or select a team in the **Team & members** tab to continue.")
    st.stop()

with generate_tab:
    selected_template = generate_team_diagnostics.render(account, selected_team, repo)

with output_tab:
    team_diagnostics_output.render(account, selected_team, selected_template)

with history_tab:
    team_diagnostics_history.render(account, selected_team)
