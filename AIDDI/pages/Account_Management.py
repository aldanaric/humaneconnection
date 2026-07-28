import streamlit as st
from repositories.account_repository import AccountRepository

from models.access_level import AccessLevel

account_repo = AccountRepository()

st.header("Manage Accounts")
st.write("Create, edit, and delete accounts")

new_account_tab, current_account_tab = st.tabs(
    ["Add Account", "Current Accounts"]
)

with new_account_tab:

    use_tab, empty_tab = st.columns([4, 1])

    with use_tab:
        with st.form("create_account_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")

            access_level = st.selectbox(
                "Access Level",
                options=list(AccessLevel),
                format_func=lambda level: level.value.replace("_", " ").title()
            )

            submitted = st.form_submit_button("Create Account")

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match")
                st.stop()
            if not username.strip() or not password:
                st.error("Username and password are required")
                st.stop()
            try:
                account_repo.create_account(
                    username,
                    password,
                    access_level,
                )
            except ValueError as e:
                st.error(str(e))
            else:
                st.success("Account created!")

with current_account_tab:

    accounts = account_repo.list_accounts()

    st.subheader("Current Accounts")

    for account in accounts:

        col1, col2, col3 = st.columns([4, 2, 1])

        with col1:
            st.write(account.account_name)

        with col2:
            st.write(account.access_level.value.replace("_", " ").title())

        with col3:
            if st.button("Manage", key=f"manage_{account.id}"):
                st.session_state.selected_account = account.id

    if "selected_account" in st.session_state:

        account = account_repo.get_account(
            st.session_state.selected_account
        )

        st.divider()
        st.subheader(f"Manage {account.account_name}")
        new_access = account.access_level

        new_password = st.text_input(
            "New Password",
            type="password",
            key=f"password_{account.id}"
        )

        if not st.session_state.selected_account == st.session_state.account.id:
            new_access = st.selectbox(
                "Access Level",
                options = list(AccessLevel),
                format_func=lambda level: level.value.replace("_", " ").title(),
                key=f"access_{account.id}"
            )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Update Account"):

                if new_password:
                    account_repo.change_password(
                        account,
                        new_password
                    )
                if new_access != account.access_level:
                    account_repo.update_access_level(
                        account,
                        new_access
                    )

                st.success("Updated!")
                del st.session_state.selected_account
                st.rerun()

        with col2:

            if not st.session_state.selected_account == st.session_state.account.id:
                confirm = st.checkbox(
                    "I understand that this will delete this account permanently"
                )
                if st.button("Delete Account") and confirm:
                    account_repo.delete_account(account.id)
                    st.success("Account deleted!")
                    del st.session_state.selected_account
                    st.rerun()
