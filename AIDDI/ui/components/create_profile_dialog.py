"""Shared create-profile dialog used by Profiles and Team Diagnostics."""
from __future__ import annotations

import streamlit as st

from repositories.profile_repository import ProfileRepository


@st.dialog("Create profile")
def open_create_profile_dialog(repo: ProfileRepository) -> None:
    """Popup form matching Growth Plan fields (first, last, employer)."""
    first_name = st.text_input("First Name", key="create_profile_dialog_first")
    last_name = st.text_input("Last Name", key="create_profile_dialog_last")
    company = st.text_input("Employer", key="create_profile_dialog_company")

    if st.button("Create profile", type="primary", use_container_width=True):
        if not first_name.strip() or not last_name.strip():
            st.error("First and last name are required.")
            return

        profile = repo.create_profile(
            first_name.strip(),
            last_name.strip(),
            company.strip(),
        )
        st.success(f"Created profile for {profile.display_name}")
        st.rerun()
