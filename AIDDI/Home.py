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

PAGES_DIR = Path(__file__).resolve().parent / "pages"

login_page = st.Page(str(PAGES_DIR / "Log_in.py"), title="Log in")
logout_page = st.Page(str(PAGES_DIR / "Log_out.py"), title="Log out")
chat_page = st.Page(str(PAGES_DIR / "1_💬_Quick_Chat.py"))

growth_plan_page = st.Page(str(PAGES_DIR / "2_Growth_Plan.py"))
knowledge_base_page = st.Page(str(PAGES_DIR / "3_Knowledge_Base.py"))
diagnostic_summary_page = st.Page(str(PAGES_DIR / "diagnostic_summary.py"), title="Diagnostic Summary")
team_diagnostics_page = st.Page(str(PAGES_DIR / "4_Team_Diagnostics.py"), title="Team Diagnostics")
saved_prompts_page = st.Page(str(PAGES_DIR / "Prompt_Editor.py"), title="Saved Prompts")
profiles_page = st.Page(str(PAGES_DIR / "Profiles.py"))
account_page = st.Page(str(PAGES_DIR / "Account_Management.py"))

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
elif account.access_level == AccessLevel.READ_ONLY:
    pg = st.navigation([
        chat_page,
        logout_page,
    ])
else:
    pg = st.navigation([login_page])

sidebar.render_sidebar()

pg.run()
