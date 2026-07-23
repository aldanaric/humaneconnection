import streamlit as st
from pypdf import PdfReader

def extract_text(uploaded_file):
    """Helper function to extract text based on file type."""
    suffix = uploaded_file.name.split('.')[-1].lower()
    
    if suffix == "pdf":
        reader = PdfReader(uploaded_file)
        pages = [page.extract_text() for page in reader.pages if page.extract_text()]
        return "\n\n".join(pages)
    else:
        # Handles .md, .csv, and standard text files
        return uploaded_file.getvalue().decode("utf-8")

def render(selected_profile, repo):
    st.subheader("Inputs: 🔗")
    st.markdown("#### 1. Client Intake Form")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**View and edit current intake data**")
        # FIX: Remove 'key' and capture the text box output into 'edited_intake'
        edited_intake = st.text_area(
            label="Current Intake Data",
            value=st.session_state.get("intake_text", ""),
            height=300,
            label_visibility="collapsed"
        )
        
        if st.button("Save Intake Form"):
            # Update the session state manually from the variable
            st.session_state.intake_text = edited_intake
            st.success("Intake form saved successfully!")
            
    with col2:
        st.markdown("**Upload replacement intake form**")
        uploaded_file = st.file_uploader(
            "Upload",
            type=["csv", "pdf", "md"],
            label_visibility="collapsed"
        )
        
        if uploaded_file and st.button("Process Uploaded File"):
            extracted_string = extract_text(uploaded_file)
            # FIX: Only update the background session state, then rerun
            st.session_state.intake_text = extracted_string
            st.rerun() 
        
    st.divider()
    
    st.markdown("#### 2. Additional Analyst Context (Optional)")
    st.markdown("Add any human observations from the intake call that the AI should consider.")
    
    col3, col4 = st.columns(2)
    with col3:
        # FIX: Same pattern for the context box
        edited_context = st.text_area(
            label="Analyst Context",
            value=st.session_state.get("analyst_context", ""),
            height=150,
            placeholder="e.g., The client seemed highly defensive when discussing team alignment..."
        )
    with col4:
        st.write("") 
        st.write("")
        if st.button("Save Analyst Context"):
            st.session_state.analyst_context = edited_context
            st.success("Analyst context saved!")