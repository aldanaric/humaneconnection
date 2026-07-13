import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image

from ui.components import sidebar

icon = Image.open("static/AIDDIlogopendingsquare.png")

st.set_page_config(
    page_title="AIDDI",
    page_icon=icon,
    layout="wide"
)


sidebar.render_sidebar()

st.markdown("Welcome to AIDDI")
st.write("AIDDI is designed to help you create high-performing teams.")
