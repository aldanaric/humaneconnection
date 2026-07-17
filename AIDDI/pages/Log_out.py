import streamlit as st
from dotenv import load_dotenv
from ui.components import sidebar

st.markdown("Thank you for using AIDDI!")
if st.button("Log out"):
    st.session_state.account = None
    st.rerun()


