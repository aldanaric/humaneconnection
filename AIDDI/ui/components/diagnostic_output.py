import streamlit as st

def render(selected_profile):
    st.selectbox("Load Previous Diagnostic Summary", ["--None--", "Initial Intake Summary - July 2026"])
    
    st.text_input("Diagnostic Summary Name", value=f"{selected_profile} - Diagnostic Summary")
    
    # Dummy text to simulate a generated report
    dummy_report = """# Observed Organizational Conditions\n...\n# Diagnostic Intelligence Findings\n...\n# Preliminary Intervention Pathway Recommendations\n..."""
    
    edit_mode = st.checkbox("Edit Summary")
    
    if edit_mode:
        st.text_area("Edit Content", value=dummy_report, height=400, label_visibility="collapsed")
    else:
        st.markdown(dummy_report)
        
    st.write("---")
    
    # Action Buttons
    st.button("Save as new Diagnostic Summary")
    st.button("Save Changes")
    st.write("")
    st.button("Download Summary markdown")
    st.button("Download Summary pdf")