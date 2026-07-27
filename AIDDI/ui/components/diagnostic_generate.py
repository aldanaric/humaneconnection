import streamlit as st
import asyncio

# Import your services
import services.diagnostic_service as diagnostic_service
from services.llm import converse  # Updated import
import services.rag as rag

def render(selected_profile, repo):
    st.subheader("Generate Summary")
    st.markdown(
        "Click below to process the intake form through the **Humane Connection™** "
        "framework and generate the early-stage intelligence report."
    )
    
    # --- NEW: Check State for UI Indicators ---
    intake_data = st.session_state.get("intake_text", "").strip()
    context_data = st.session_state.get("analyst_context", "").strip()
    
    # Required Input Indicator
    if intake_data:
        st.success("Intake Form is present")
    else:
        st.error("Missing Intake Form. Return to inputs.")
        
    # Optional Input Indicator (Using info/blue for optional, or you can make it success/green)
    if context_data:
        st.success("Analyst Context is present")
    else:
        st.info("Analyst Context is empty (Optional)")

    # --- NEW: Disable the button if the required intake data is missing ---
    is_ready = bool(intake_data)
    
    if st.button("Generate Diagnostic Intelligence Summary", type="primary"):
        # 1. Validation
        intake_data = st.session_state.get("intake_text", "").strip()
        if not intake_data:
            st.error("Missing Intake Data: Please upload and save the intake form in the Inputs tab first.")
            return
            
        context_data = st.session_state.get("analyst_context", "").strip()
        output_placeholder = st.empty()
        
        # 2. Retrieve RAG Context First
        with st.spinner("Retrieving relevant intervention pathways from Knowledge Base..."):
            try:
                # Combine the intake and context to search the index
                search_query = f"{intake_data}\n{context_data}"
                
                # Call the specific function from your rag.py file
                retrieved_data = rag.retrieve_context(search_query, top_k=3)
                
                # Extract the pre-formatted string containing all the chunks
                rag_context = retrieved_data["combined_context"]
                
            except rag.RAGNotReadyError as e:
                # Catch the specific error you defined if the index needs to be rebuilt
                st.error(str(e))
                return
            except Exception as e:
                # Fallback in case no passages are found or another error occurs
                st.warning(f"RAG Retrieval failed, proceeding without context. Error: {e}")
                rag_context = ""
        
        # 3. Build the Prompts using the Service
        try:
            system_prompt = diagnostic_service.load_system_prompt()
        except FileNotFoundError as e:
            st.error(str(e))
            return
            
        # Build the final prompt using intake, analyst context, and the RAG context
        user_prompt = diagnostic_service.build_user_prompt(intake_data, context_data, rag_context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        # 4. Stream Generation using the correct converse function
        async def generate_summary():
            full_response = ""
            # Updated to call converse directly
            async for chunk in converse(messages, max_tokens=8192):
                full_response += chunk
                output_placeholder.markdown(full_response + "▌")
                
            output_placeholder.markdown(full_response)
            return full_response

        # 5. Execute
        with st.spinner("Processing signals through Humane Connection™..."):
            try:
                final_report = asyncio.run(generate_summary())
                
                # Save locally and to session state
                diagnostic_service.save_diagnostic_summary(selected_profile, final_report)
                st.session_state.diagnostic_output = final_report
                st.session_state.generated_diagnostic_summary = final_report
                
                st.success("Summary generated successfully! Navigate to the Outputs tab to review and edit.")
                
            except Exception as exc:
                st.exception(exc)
