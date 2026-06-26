import asyncio
import streamlit as st

from services import prompts
from ui.components import sidebar
from ui.interactions import chat_handler, book_handler

st.set_page_config(
    page_title="Quick Chat",
    page_icon="💬",
    layout="wide"
)

sidebar.show()

st.header("Quick Chat")
st.write("Get instant answers to your Humane Connection questions.")
ask_book = st.checkbox("Use The Humane Connection context.", value=False)

# Ensure the session state is initialized
if "messages" not in st.session_state:
    initial_messages = [{
        "role": "system",
        "content": prompts.quick_chat_system_prompt()
    }]
    st.session_state.messages = initial_messages

# Print all messages in the session state
for message in [m for m in st.session_state.messages if m["role"] != "system"]:
    avatar = "🔎" if message["role"] == "evidence" else None

    if avatar:
        with st.chat_message(message["role"], avatar=avatar):
            page_number = message.get("page_number")
            image_data = message.get("image_data")
            context = message.get("content", "")

            with st.expander(
                f"See page {page_number}" if page_number is not None else "Evidence",
                expanded=False
            ):
                if page_number is not None:
                    st.write(f"Page Number: {page_number}")

                if image_data:
                    st.image(image_data, caption=f"Page {page_number}")

                if context:
                    st.write(context)
    else:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# React to the user prompt
if prompt := st.chat_input("Ask a  question."):
    if ask_book:
        asyncio.run(book_handler.ask_book(st.session_state.messages, prompt))
        st.rerun()
    else:
        # Filter out evidence messages before sending to the normal LLM chat path
        filtered_messages = [
            m for m in st.session_state.messages
            if m["role"] in {"system", "user", "assistant"}
        ]
        st.session_state.messages = filtered_messages

        asyncio.run(chat_handler.chat(st.session_state.messages, prompt))
        st.rerun()