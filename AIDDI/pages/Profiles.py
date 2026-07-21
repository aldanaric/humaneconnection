import streamlit as st

from repositories.profile_repository import ProfileRepository
from repositories.account_repository import AccountRepository

st.header("Profiles")

account = st.session_state.get("account")

account_repo = AccountRepository()

repo = ProfileRepository(account_repo.get_profiles_root(account))

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

