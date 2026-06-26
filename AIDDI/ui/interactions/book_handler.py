import streamlit as st
import services.rag

async def ask_book(messages, prompt):
    """
    Handles the UI flow for asking questions about "Humane Connection",
    including displaying user messages, processing RAG responses, and updating the chat history.

    Args:
        messages: List of message dictionaries with conversation history
        prompt: The user's question about the book

    Returns:
        Updated messages list with the new conversation
    """
    # Add the user's message to the conversation history
    messages.append({"role": "user", "content": prompt})

    # 1. Display user's prompt in chat UI
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Create placeholder for spinner
    spinner_placeholder = st.empty()

    # 3. Inside assistant chat message
    with st.chat_message("assistant"):
        # a. Show loading spinner
        with spinner_placeholder:
            with st.spinner("Asking the Humane Connection context..."):
                try:
                    # b. Call RAG service
                    rag_result = await services.rag.ask_book(prompt, return_image=True)
                    st.write({"debug_rag_result_type": str(type(rag_result))})

                    if rag_result is None:
                        rag_result = {
                            "answer": ":red[services.rag.ask_book returned None.]",
                            "context": "",
                            "page_number": None,
                            "image_data": None
                        }

                except Exception as e:
                    rag_result = {
                        "answer": f":red[RAG error: {e}]",
                        "context": "",
                        "page_number": None,
                        "image_data": None
                    }

                # c. Extract returned values
                answer = rag_result["answer"]
                context = rag_result["context"]
                page_number = rag_result["page_number"]
                image_data = rag_result["image_data"]

        # d. Clear spinner
        spinner_placeholder.empty()

        # 4. Display response
        st.write(answer)

        # 5. Create evidence section
        with st.expander(
            f"Evidence{f': page {page_number}' if page_number is not None else ''}",
            expanded=False
        ):
            if page_number is not None:
                st.write(f"Page Number: {page_number}")

            if image_data:
                st.image(image_data, caption=f"Page {page_number}")

            if context:
                st.write(context)

        # 6. Update chat history
        messages.append({"role": "assistant", "content": answer})
        messages.append({
            "role": "evidence",
            "content": context,
            "page_number": page_number,
            "image_data": image_data
        })

        # 7. Update session state
        st.session_state.messages = messages

    # 8. Return messages
    return messages