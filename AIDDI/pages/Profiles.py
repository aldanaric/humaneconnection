import streamlit as st

from repositories.profile_repository import ProfileRepository

st.header("Profiles")

repo = ProfileRepository()

profiles = repo.list_profiles()

options = [
    "--Select a profile--",
    *profiles,
    "+ Add new profile"
]

selected_profile = ""

selected=st.selectbox(
    "Select Person",
    options,
    format_func=lambda x: x.display_name if hasattr(x, "display_name") else x
)

if selected == "+ Add new profile":
    st.subheader("Create new Profile:")

elif selected == "--Select a profile--":
    st.stop()

else:
    selected_profile = selected

if not selected_profile:
    st.stop()

st.header("Contents")

profile_contents = repo.list_profile_files(selected_profile)

for file in profile_contents:
    st.write(file)

