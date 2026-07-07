from models.profile import Profile
from repositories.profile_repository import ProfileRepository
import streamlit as st

from models.document_type import DocumentType

from services import observations

from models.observation import Observation


def render(profile: Profile, repo: ProfileRepository):
    st.subheader("Inputs:")

    st.markdown("1. Personality Assessment")

    if not repo.document_exists(
        profile,
        DocumentType.PERSONALITY
    ):
        personality_upload = st.file_uploader(
            "Personality Assessment",
            type=["md", "pdf"])
        if personality_upload is not None:
            repo.upload_document(profile, DocumentType.PERSONALITY, personality_upload)
    else:
        col1, col2 = st.columns(2)
        with col1:
            personality = repo.load_document(profile, DocumentType.PERSONALITY)

            edited = st.text_area(
                "View and edit current personality assessment",
                value=personality,
                height=400
            )
        with col2:
            personality_upload = st.file_uploader(
                "Upload replacement personality assessment",
                type=["md", "pdf"]
            )
            if personality_upload is not None:
                repo.upload_document(profile, DocumentType.PERSONALITY, personality_upload)

            if st.button("Save Personality assessment"):
                repo.save_document(
                    profile,
                    DocumentType.PERSONALITY,
                    edited
                )
                st.success("Saved.")

    st.markdown("2. Job Functions")
    col1, col2 = st.columns(2)
    with col1:
        job_functions = repo.load_document(
            profile,
            DocumentType.JOB_FUNCTIONS,
        )
        edited = st.text_area(
            "Job title and functions",
            value=job_functions,
            height=400,
        )

    with col2:
        job_functions_upload = st.file_uploader(
            "Upload file with job title and functions",
            type=["md", "pdf"]
        )
        if job_functions_upload is not None:
            repo.upload_document(profile, DocumentType.JOB_FUNCTIONS, job_functions_upload)
        if st.button("Save Job Functions"):
            repo.save_document(
                profile,
                DocumentType.JOB_FUNCTIONS,
                edited
            )
            st.success("Saved.")

    st.markdown("3. Areas for Improvement")
    key = f"observations_{profile.id}"
    if key not in st.session_state:
        observations_file = repo.load_document(profile, DocumentType.OBSERVATIONS)
        st.session_state[key] = observations.parse_observations(observations_file)
    observations_list = st.session_state[key]
    for i, obs in enumerate(observations_list):
        with st.container(border=True):
            area_key = f"{profile.id}_area_{i}"
            if area_key not in st.session_state:
                st.session_state[area_key] = obs.area
            obs.area = st.text_input(
                f"**Area {i + 1} for Improvement**:",
                key=area_key
            )
            col1, col2 = st.columns(2)
            with col1:
                observation_key = f"{profile.id}_observation_{i}"
                if observation_key not in st.session_state:
                    st.session_state[observation_key] = obs.observation
                obs.observation = st.text_area(
                    "Observation",
                    key=observation_key,
                    height=100,
                )
            with col2:
                impact_key = f"{profile.id}_impact_{i}"
                if impact_key not in st.session_state:
                    st.session_state[impact_key] = obs.impact
                obs.impact = st.text_area(
                    "Impact",
                    key=impact_key,
                    height=100
                )
            if st.button(
                "Delete",
                key=f"{profile.id}_delete_{i}"
            ):
                observations_list.pop(i)
                st.rerun()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add another observation"):
            observations_list.append(
                Observation("", "", "")
            )
            st.rerun()
    with col2:
        if st.button("Save Areas for Improvement"):
            for i, obs in enumerate(observations_list):
                obs.area = st.session_state[f"{profile.id}_area_{i}"]

                obs.observation = st.session_state[
                    f"{profile.id}_observation_{i}"
                ]

                obs.impact = st.session_state[
                    f"{profile.id}_impact_{i}"
                ]
            observation_markdown = observations.observations_to_markdown(observations_list)
            repo.save_document(
                profile,
                DocumentType.OBSERVATIONS,
                observation_markdown
            )
            st.success("Saved.")
