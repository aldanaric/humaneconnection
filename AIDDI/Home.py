import streamlit as st
from dotenv import load_dotenv

from ui.components import sidebar


st.set_page_config(
    page_title="AIDDI",
    page_icon="🐥",
    layout="wide"
)


sidebar.render_sidebar()

st.toast("Welcome to AIDDI!", icon="🐥")

st.markdown("Welcome to AIDDI")
st.write("AIDDI is designed to help you create high-performing teams.")
