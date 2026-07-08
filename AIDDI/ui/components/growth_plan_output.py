import streamlit as st

from models.profile import Profile
from repositories.profile_repository import ProfileRepository
from models.document_type import DocumentType
from models.growth_plan import GrowthPlan
from services.pdf_export import markdown_to_pdf

def render(profile: Profile, repo: ProfileRepository, NoPlan):

    st.session_state.editor = st.session_state.generated_growth_plan

    saved_plans = repo.list_growth_plans(profile)

    selected_saved_plan = st.selectbox(
        "Load Previous Growth Plan",
        ["--None--"] + saved_plans,
        format_func=lambda p: p.title
        if p != "--None--"
        else p
    )

    if selected_saved_plan != "--None--":
        st.session_state.current_plan = selected_saved_plan
        st.session_state.editor = selected_saved_plan.content

    plan_name = st.text_input(
        "Growth Plan Name",
        value=st.session_state.current_plan.title
        if st.session_state.current_plan is not None
        else profile.display_name + " growth plan"
    )

    st.markdown(
        st.session_state.editor,
        unsafe_allow_html=False
    )
    if st.checkbox("Edit plan"):
        edited = st.text_area(
            "Review and edit the wording for the generated growth plan",
            value=st.session_state.editor,
            height=800
        )
    else:
        edited = st.session_state.editor

    if st.button(
        "Save as new Growth Plan",
        disabled=st.session_state.editor==NoPlan,
    ):
        new_plan = repo.save_growth_plan(
            profile,
            edited,
            plan_name
        )
        st.session_state.current_plan = new_plan
        st.success(f"Saved {new_plan.title}")

    if st.button(
        "Save Changes",
        disabled=(
            "current_plan"
            not in st.session_state
        )
    ):
        plan = st.session_state.current_plan
        plan.content = edited

        updated = repo.update_growth_plan(plan)

        st.session_state.current_plan = updated

    st.download_button(
        "Download Growth Plan markdown",
        data=edited,
        file_name=f"{profile.display_name} growth plan.md",
        mime="text/markdown",
        disabled=st.session_state.editor==NoPlan
    )
    pdf_bytes = markdown_to_pdf(edited)

    st.download_button(
        "Download Growth Plan pdf",
        data=pdf_bytes,
        file_name=f"{profile.display_name} growth plan.pdf",
        mime="application/pdf",
        disabled=st.session_state.editor==NoPlan
    )
