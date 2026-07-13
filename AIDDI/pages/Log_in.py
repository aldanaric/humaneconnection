import streamlit as st
from dotenv import load_dotenv
from ui.components import sidebar

st.markdown("Welcome to AIDDI")
st.write("AIDDI is designed to help you create high-performing teams.")
if st.button("Log in"):
    st.session_state.logged_in = True
    st.rerun()

if st.button("Log in as admin"):
    st.session_state.logged_in = True
    st.session_state.admin = True
    st.rerun()


