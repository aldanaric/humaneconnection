import streamlit as st
from repositories.account_repository import AccountRepository

from models.access_level import AccessLevel

account_repo = AccountRepository()

st.header("Manage Accounts")
st.header("Create, edit, and delete accounts")

username = st.text_input("Username")
password = st.text_input("Password", type="password")
confirm_password = st.text_input("Confirm password", type="password")
if password != confirm_password:
    st.error("Passwords do not match")

access_level = st.selectbox(
    "Access Level",
    options=list(AccessLevel),
    format_func=lambda level: level.value.replace("_", " ").title()
)

if st.button("Create Account"):
    account_repo.create_account(
        username,
        password,
        access_level,
    )
    st.success("Account created!")
