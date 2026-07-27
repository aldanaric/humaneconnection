import streamlit as st

from models.profile import Profile
from repositories.profile_repository import ProfileRepository
from services.pdf_export import markdown_to_pdf
import services.diagnostic_service as diagnostic_service

def render(profile: Profile, repo: ProfileRepository, NoSummary: str):
    
    # 1. State Management & Empty State Handling
    # Ensures we have a fallback if the Generate tab hasn't run yet
    if "generated_diagnostic_summary" not in st.session_state:
        st.session_state.generated_diagnostic_summary = NoSummary
        
    st.session_state.diag_editor = st.session_state.generated_diagnostic_summary

    # Check for an existing saved summary on disk for this profile
    saved_file_path = diagnostic_service.output_path(profile)
    
    options = ["--None--"]
    if saved_file_path.exists():
        options.append(saved_file_path.name)

    selected_saved = st.selectbox(
        "Load Previous Diagnostic Summary",
        options
    )

    # If the analyst selects a previously saved file, load its content
    if selected_saved != "--None--":
        saved_content = saved_file_path.read_text(encoding="utf-8")
        st.session_state.current_diag_summary_name = saved_file_path.name
        st.session_state.diag_editor = saved_content

    summary_name = st.text_input(
        "Diagnostic Summary Name",
        value=st.session_state.get("current_diag_summary_name", f"{profile.display_name} - Diagnostic Summary")
    )

    # 2. Display & Edit Mode
    st.markdown(
        st.session_state.diag_editor,
        unsafe_allow_html=False
    )
    
    if st.checkbox("Edit Summary"):
        edited = st.text_area(
            "Review and edit the wording for the generated summary",
            value=st.session_state.diag_editor,
            height=800
        )
    else:
        edited = st.session_state.diag_editor

    # 3. Save Functionality
    # Adapts to diagnostic_service which utilizes a single output path per profile
    if st.button(
        "Save Diagnostic Summary",
        disabled=st.session_state.diag_editor == NoSummary,
    ):
        try:
            saved_path = diagnostic_service.save_diagnostic_summary(profile, edited)
            st.session_state.current_diag_summary_name = saved_path.name
            # Push manual edits back to session state so they persist across tab navigation
            st.session_state.generated_diagnostic_summary = edited
            st.success(f"Saved {saved_path.name}")
        except Exception as e:
            st.error(f"Failed to save summary: {e}")

    # 4. Export / Download
    st.download_button(
        "Download Summary markdown",
        data=edited,
        file_name=f"{profile.display_name} Diagnostic Summary.md",
        mime="text/markdown",
        disabled=st.session_state.diag_editor == NoSummary
    )
    
    try:
        pdf_bytes = markdown_to_pdf(edited)
        st.download_button(
            "Download Summary pdf",
            data=pdf_bytes,
            file_name=f"{profile.display_name} Diagnostic Summary.pdf",
            mime="application/pdf",
            disabled=st.session_state.diag_editor == NoSummary
        )
    except Exception as e:
        st.error(f"PDF generation failed. Ensure wkhtmltopdf (or your PDF rendering engine) is configured properly. Error: {e}")