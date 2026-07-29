import streamlit as st
from dotenv import load_dotenv
from ui.components import sidebar

from repositories.account_repository import AccountRepository

from models.access_level import AccessLevel

account_repo = AccountRepository()

st.markdown("Welcome to AIDDI")
st.write("AIDDI is designed to help you create high-performing teams.")

use_col, empty_col = st.columns([4, 2])

with use_col:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

if st.button("Log in"):
    account = account_repo.authenticate(username, password)
    if account:
        st.session_state.account = account
        st.write(st.session_state.account)
    else:
        st.error("Invalid username or password")
    st.rerun()





@st.dialog("Create Account")
def create_account_dialog():
    with st.form("create_account_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        if password != confirm_password:
            st.error("Passwords do not match")
        submitted = st.form_submit_button("Create Account")

    if submitted:
        try:
            account_repo.create_account(
                username,
                password,
                AccessLevel.READ_ONLY,
            )
        except ValueError as e:
            st.error(str(e))
        else:
            st.success("Account created!")

if st.button("Create Account"):
    create_account_dialog()
