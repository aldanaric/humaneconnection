import streamlit as st

def render(selected_profile):
    st.subheader("Inputs: 🔗")
    
    st.markdown("#### 1. Client Intake Form")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**View and edit current intake data**")
        # Text area to display previously uploaded or currently active text
        st.text_area(
            label="Current Intake Data",
            value="No intake data loaded yet. Upload a Microsoft Form export.",
            height=300,
            label_visibility="collapsed"
        )
        
    with col2:
        st.markdown("**Upload replacement intake form**")
        st.file_uploader(
            "Upload",
            type=["csv", "pdf", "md"],
            label_visibility="collapsed"
        )
        st.button("Save Intake Form")
        
    st.divider()
    
    st.markdown("#### 2. Additional Analyst Context (Optional)")
    st.markdown("Add any human observations from the intake call that the AI should consider.")
    
    col3, col4 = st.columns(2)
    with col3:
        st.text_area(
            label="Analyst Context",
            value="",
            height=150,
            placeholder="e.g., The client seemed highly defensive when discussing team alignment..."
        )
    with col4:
        st.write("") # Spacing
        st.write("")
        st.button("Save Analyst Context")