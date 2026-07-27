import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image

from models.access_level import AccessLevel
from ui.components import sidebar



if "account" not in st.session_state:
    st.session_state.account = None
    account = None
else:
    account = st.session_state.get("account")

icon = Image.open("static/AIDDIlogopendingsquare.png")

login_page = st.Page("pages/Log_in.py", title="Log in")
logout_page = st.Page("pages/Log_out.py", title="Log out")
chat_page = st.Page("pages/1_💬_Quick_Chat.py")

growth_plan_page = st.Page("pages/2_Growth_Plan.py")
knowledge_base_page = st.Page("pages/3_Knowledge_Base.py")
diagnostic_summary_page = st.Page("pages/diagnostic_summary.py", title="Diagnostic Summary")
team_diagnostics_page = st.Page("pages/4_Team_Diagnostics.py", title="Team Diagnostics")
saved_prompts_page = st.Page("pages/Prompt_Editor.py", title="Saved Prompts")
profiles_page = st.Page("pages/Profiles.py")
account_page = st.Page("pages/Account_Management.py")

if account is None:
    pg = st.navigation([login_page])
elif account.access_level == AccessLevel.ADMIN:
    pg = st.navigation([
        chat_page,
        growth_plan_page,
        team_diagnostics_page,
        diagnostic_summary_page,
        knowledge_base_page,
        saved_prompts_page,
        profiles_page,
        account_page,
        logout_page,
    ])
elif account.access_level == AccessLevel.USER:
    pg = st.navigation([
        chat_page,
        growth_plan_page,
        team_diagnostics_page,
        diagnostic_summary_page,
        profiles_page,
        logout_page,
    ])
else:
    pg = st.navigation([login_page])

sidebar.render_sidebar()

pg.run()