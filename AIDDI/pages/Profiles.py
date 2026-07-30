import streamlit as st
import pandas as pd

from repositories.profile_repository import ProfileRepository
from repositories.account_repository import AccountRepository

from models.access_level import AccessLevel
from ui.components.create_profile_dialog import open_create_profile_dialog

st.header("Profiles")

account = st.session_state.get("account")
if account is None:
    st.warning("Log in to view profiles.")
    st.stop()

account_repo = AccountRepository()
own_repo = ProfileRepository(account.id)

if st.button("Create profile", type="primary"):
    open_create_profile_dialog(own_repo)

if account.access_level == AccessLevel.ADMIN:
    rows = []
    for acct in account_repo.list_accounts():
        repo = ProfileRepository(acct.id)

        for profile in repo.list_profiles():
            rows.append({
                "Name": profile.first_name + " " + profile.last_name,
                "Company": profile.company_name,
                "profile": profile,
                "repo": repo,
                "Owner": acct.account_name
            })
else:
    rows = [
        {
            "Name": p.first_name + " " + p.last_name,
            "Company": p.company_name,
            "profile": p,
            "repo": own_repo,
            "Owner": account.account_name
        }
        for p in own_repo.list_profiles()
    ]

if not rows:
    st.info("No profiles found. Create one to get started.")
    st.stop()

df = pd.DataFrame(rows)

selected_profile = None

if account.access_level == AccessLevel.ADMIN:
    event = st.dataframe(
        df[["Name", "Company", "Owner"]],
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key=f"profile_table_{account.access_level.value}"
    )
else:
    event = st.dataframe(
        df[["Name", "Company"]],
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key=f"profile_table_{account.access_level.value}"
    )

if event.selection.rows:

    index = event.selection.rows[0]

    selected_profile = df.iloc[index]["profile"]
    repo = df.iloc[index]["repo"]

    st.session_state.pop("preview", None)

    inputs_tab, growth_tab = st.tabs(
        ["Uploaded documents", "Growth Plans"]
    )

    files = repo.list_documents(selected_profile)
    plans = repo.list_growth_plans(selected_profile)

    with inputs_tab:

        if not files:
            st.info("No uploaded files found")

        for file in files:

            col1, col2 = st.columns([4,1])

            with col1:
                st.write(file.name)

            with col2:
                if st.button("Preview", key=f"doc_{file.id}"):
                    st.session_state.preview = repo.load_profile_document(
                        selected_profile,
                        file
                    )

    with growth_tab:

        if not plans:
            st.info("No growth plans generated")

        for plan in plans:
            col1, col2 = st.columns([4,1])

            with col1:
                st.write(plan.title)

            with col2:
                if st.button("Preview", key=f"plan_{plan.id}"):
                    st.session_state.preview = plan.content

    if "preview" in st.session_state:
        with st.container(height=500):
            st.markdown(
                st.session_state.preview,
                unsafe_allow_html=False
            )
