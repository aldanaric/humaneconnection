import asyncio
from pathlib import Path

import streamlit as st

from services import prompts
from ui.components import sidebar
from ui.interactions import chat_handler, book_handler

logo = Path(__file__).resolve().parents[1] / "static" / "AIDDIlogopendingsquare.png"
# --- Page Configuration ---
st.set_page_config(
    page_title="Quick Chat",
    page_icon=logo,
    layout="wide"
)

#sidebar.show()

st.header("Quick Chat")
st.write("Get instant answers to your Humane Connection questions.")

# Toggle for Retrieval-Augmented Generation (RAG) vs Standard Chat
ask_book = st.checkbox("Use Humane Connection", value=True, key="quick_chat_use_humane_connection")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    initial_messages = [{
        "role": "system",
        "content": prompts.quick_chat_system_prompt()
    }]
    st.session_state.messages = initial_messages

# --- Render Conversation History ---
# Iterate through all non-system messages to display them on the UI
for message in [m for m in st.session_state.messages if m["role"] != "system"]:
    # Special handling for "evidence" messages returned by the book handler
    avatar = "🔎" if message["role"] == "evidence" else None

    if avatar:
        with st.chat_message(message["role"], avatar=avatar):
            page_number = message.get("page_number")
            document_name = message.get("document_name")
            location = message.get("location")
            image_data = message.get("image_data")
            context = message.get("content", "")

            with st.expander(
                f"See page {page_number}" if page_number is not None else "Evidence",
                expanded=False
            ):
                if document_name:
                    st.write(f"Source: {document_name}")
                if location:
                    st.write(f"Location: {location}")
                elif page_number is not None:
                    st.write(f"Page Number: {page_number}")
                if image_data:
                    st.image(image_data, caption=f"Page {page_number}")
                if context:
                    st.write(context)
    else:
        # Standard user or assistant message rendering
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- Handle New User Input ---
if prompt := st.chat_input("Ask a question."):

    # Pathway A: RAG / Document Chat
    if ask_book:
        asyncio.run(book_handler.ask_book(st.session_state.messages, prompt))
        st.rerun()

    # Pathway B: Standard LLM Chat via Factory Pattern
    else:
        asyncio.run(chat_handler.chat(st.session_state.messages, prompt))
        st.rerun()
