import streamlit as st

from models.profile import Profile
from repositories.profile_repository import ProfileRepository
from models.document_type import DocumentType
from services.pdf_export import markdown_to_pdf

def render(profile: Profile, repo: ProfileRepository, NoPlan):

    current_plan = st.session_state.generated_growth_plan

    saved_plans = repo.list_growth_plans(profile)

    selected_saved_plan = st.selectbox(
        "Load Previous Growth Plan",
        ["--None--"] + saved_plans,
        format_func=lambda p: (
            p.stem.replace("_", " ")
            if p != "--None--"
            else p
        )
    )

    if selected_saved_plan != "--None--":
        st.session_state.generated_growth_plan = (
            repo.load_growth_plan(selected_saved_plan)
        )
        st.session_state.current_plan_path = selected_saved_plan

    plan_name = st.text_input(
        "Growth Plan Name",
        value=profile.display_name + " Growth Plan"
    )

    st.markdown(
        current_plan,
        unsafe_allow_html=False
    )
    if st.checkbox("Edit plan"):
        edited = st.text_area(
            "Review and edit the wording for the generated growth plan",
            value=current_plan,
            height=800
        )
    else:
        edited = current_plan
    if st.button(
        "Save as new Growth Plan",
        disabled=current_plan==NoPlan,
    ):
        path = repo.save_growth_plan(
            profile,
            edited,
            plan_name
        )
        st.session_state.current_plan_path = path

        st.success(f"Saved {path.name}")
    if st.button(
        "Save Changes",
        disabled=(
            "current_plan_path"
            not in st.session_state
        )
    ):
        st.session_state.current_plan_path.write_text(
            edited,
            encoding="utf-8"
        )
    st.download_button(
        "Download Growth Plan markdown",
        data=edited,
        file_name=f"{profile.display_name} growth plan.md",
        mime="text/markdown",
        disabled=current_plan==NoPlan
    )
    pdf_bytes = markdown_to_pdf(edited)

    st.download_button(
        "Download Growth Plan pdf",
        data=pdf_bytes,
        file_name=f"{profile.display_name} growth plan.pdf",
        mime="application/pdf",
        disabled=current_plan==NoPlan
    )
