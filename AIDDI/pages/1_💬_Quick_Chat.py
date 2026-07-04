import asyncio
import streamlit as st

from services import prompts
from ui.components import sidebar
from ui.interactions import chat_handler, book_handler
from services.llm_factory import get_llm

# --- Page Configuration ---
st.set_page_config(
    page_title="Quick Chat",
    page_icon="💬",
    layout="wide"
)

sidebar.show()

st.header("Quick Chat")
st.write("Get instant answers to your Humane Connection questions.")

# Toggle for Retrieval-Augmented Generation (RAG) vs Standard Chat
ask_book = st.checkbox("Use The Humane Connection context.", value=False)

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
        # 1. Filter out UI-specific evidence messages before sending history to the LLM
        filtered_messages = [
            m for m in st.session_state.messages
            if m["role"] in {"system", "user", "assistant"}
        ]
        st.session_state.messages = filtered_messages

        # 2. Append and immediately render the user's prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 3. Initialize the currently configured LLM
        provider = get_llm()

        # 4. Define an async helper to stream the token chunks to the UI inline
        async def stream_llm_response():
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # Fetch streamed chunks from whatever provider the factory returned
                async for chunk in provider.converse(st.session_state.messages):
                    full_response += chunk
                    # Render with a typewriter cursor
                    response_placeholder.markdown(full_response + "▌")
                
                # Final render without the cursor
                response_placeholder.markdown(full_response)
                return full_response

        # 5. Execute the stream and capture the complete text
        final_text = asyncio.run(stream_llm_response())

        # 6. Save the AI's final response to the session state
        st.session_state.messages.append({"role": "assistant", "content": final_text})
        
        # 7. Rerun to sync Streamlit's UI state
        st.rerun()