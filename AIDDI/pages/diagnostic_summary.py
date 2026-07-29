import streamlit as st
from pathlib import Path

# --- Architecture Imports ---
from models.account import Account
from repositories.account_repository import AccountRepository
from repositories.profile_repository import ProfileRepository

# --- UI Component Imports ---
from ui.components import diagnostic_inputs
from ui.components import diagnostic_generate
from ui.components import diagnostic_output

NO_GENERATED_SUMMARY = "No summary has been generated this session"

logo = Path(__file__).resolve().parents[1] / "static" / "AIDDIlogopendingsquare.png"

st.set_page_config(
    page_title="Diagnostic Intelligence Summary",
    page_icon=logo,
    layout="wide"
)

st.header("Diagnostic Intelligence Summary")

# --- 1. Load the Actual Profiles (Matching Growth Plan) ---
account = st.session_state.get("account")

# Stop execution if no account is found
if account is None:
    st.warning("Please log in to view this page.")
    st.stop()

repo = ProfileRepository(account.id)

profiles = repo.list_profiles()

options = [
    "--Select a profile--",
    *profiles,
    "+ Add new profile"
]

selected_profile = None

selected = st.selectbox(
    "Select Client / Profile",
    options,
    format_func=lambda x: x.display_name if hasattr(x, "display_name") else x
)

if selected == "+ Add new profile":
    st.subheader("Create new Profile:")
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    company = st.text_input("Employer")

    if st.button("Create profile"):
        profile = repo.create_profile(first_name, last_name, company)
        st.success(f"Created profile for {profile.display_name}")
        st.rerun()

elif selected == "--Select a profile--":
    st.stop()
else:
    selected_profile = selected

if not selected_profile:
    st.stop()

# --- 2. Initialize & Reset Session State ---
# If the user switches to a different profile, clear the old data
if (
    "current_diagnostic_profile_id" not in st.session_state
    or st.session_state.current_diagnostic_profile_id != selected_profile.id
):
    st.session_state.current_diagnostic_profile_id = selected_profile.id
    st.session_state.intake_text = ""
    st.session_state.analyst_context = ""
    st.session_state.diagnostic_output = ""
    st.session_state.generated_diagnostic_summary = NO_GENERATED_SUMMARY

# --- 3. Tabs Setup ---
inputs_tab, generate_tab, output_tab = st.tabs(
    ["Inputs", "Generate", "Outputs"]
)

# --- 4. Render Components (passing the repo so they can save files later) ---
with inputs_tab:
    diagnostic_inputs.render(selected_profile, repo)

with generate_tab:
    diagnostic_generate.render(selected_profile, repo)

with output_tab:
    diagnostic_output.render(selected_profile, repo, NO_GENERATED_SUMMARY)
