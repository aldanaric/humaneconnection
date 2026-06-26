from typing import List, Dict, Union, Tuple

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

import services.llm

async def run_conversation(messages: List[Dict[str, str]], message_placeholder: Union[DeltaGenerator, None] = None, max_tokens: int = 1600) \
        -> Tuple[List[Dict[str, str]], str]:
    """
    Runs a conversation with the LLM service and handles streaming the response.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        message_placeholder: Optional Streamlit placeholder for displaying streaming response
        max_tokens: Maximum number of tokens to generate (default 1600)
        
    Returns:
        Tuple containing updated messages list and the full response string
    """
    full_response = ""

    chunks = services.llm.converse(messages, max_tokens=max_tokens)
    chunk = await anext(chunks, "END OF CHAT")
    while chunk != "END OF CHAT":
        print(f"Received chunk from LLM service: {chunk}")
        if chunk.startswith("EXCEPTION"):
            full_response = full_response
            #":red[We are having trouble generating advice.  Please wait a minute and try again.]" + full_response + chunk
            break
        full_response = full_response + chunk

        if message_placeholder is not None:
            message_placeholder.code(full_response + "▌")

        chunk = await anext(chunks, "END OF CHAT")

    if message_placeholder is not None:
        message_placeholder.code(full_response)

    messages.append({"role": "assistant", "content": full_response})
    return messages, full_response


async def chat(messages, prompt):
    """
    Handles the chat UI flow, including displaying user messages, 
    processing LLM responses, and updating the chat history.
    
    Args:
        messages: List of message dictionaries with conversation history
        prompt: The user's input prompt
        
    Returns:
        Updated messages list with the new conversation
    """
    # Add the user's message to the conversation history
    messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    message_placeholder = st.empty()
    spinner_placeholder = st.empty()

    with st.chat_message("assistant"):
        # Step 1: Display spinner while processing the response
        with spinner_placeholder:
            with st.spinner("Receiving response..."):
                messages, response = await run_conversation(messages, message_placeholder)

        message_placeholder.empty()  # Clear the streamed chunks
        spinner_placeholder.empty()  # Clear the spinner

        # Display the final response
        st.write(response)

        st.session_state.messages = messages
    return messages
