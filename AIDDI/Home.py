import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image

from ui.components import sidebar

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "admin" not in st.session_state:
    st.session_state.admin = False

icon = Image.open("static/AIDDIlogopendingsquare.png")

login_page = st.Page("pages/Log_in.py", title="Log in")
logout_page = st.Page("pages/Log_out.py", title="Log out")
chat_page = st.Page("pages/1_💬_Quick_Chat.py")
growth_plan_page = st.Page("pages/2_Growth_Plan.py")
knowledge_base_page = st.Page("pages/3_Knowledge_Base.py")
rag_status_page = st.Page("pages/4_RAG_Status.py")

if st.session_state.logged_in and st.session_state.admin:
    pg = st.navigation(
        [chat_page, growth_plan_page, knowledge_base_page, rag_status_page, logout_page]
    )
elif st.session_state.logged_in:
    pg = st.navigation([chat_page, growth_plan_page, logout_page])
else:
    pg = st.navigation([login_page])

st.set_page_config(
    page_title="AIDDI",
    page_icon=icon,
    layout="wide"
)

sidebar.render_sidebar()

pg.run()




