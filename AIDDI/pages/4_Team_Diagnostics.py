from pathlib import Path

import streamlit as st

from ui.components import team_diagnostics_prompt
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
    "Upload team assessments, choose a saved prompt, and generate a facilitator packet."
)

# Sidebar is rendered by Home.py
team_diagnostics.init_prompt_templates()

prompt_tab, team_tab, generate_tab, output_tab = st.tabs(
    [
        "Prompt template",
        "Team & members",
        "Generate",
        "Output",
    ]
)

with prompt_tab:
    selected_template = team_diagnostics_prompt.render()

with team_tab:
    selected_team = team_diagnostics_team.render()

if not selected_template:
    st.stop()

if not selected_team:
    st.info("Create or select a team in the **Team & members** tab to continue.")
    st.stop()

with generate_tab:
    generate_team_diagnostics.render(selected_team, selected_template)

with output_tab:
    team_diagnostics_output.render(selected_team, selected_template)
