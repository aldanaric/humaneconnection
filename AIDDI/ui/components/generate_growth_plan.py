import streamlit as st
import asyncio
from models.profile import Profile

from repositories.profile_repository import ProfileRepository

from services import growth_plan

from ui.interactions import chat_handler


def render(profile: Profile, repo: ProfileRepository):

    growth_inputs = repo.validate_growth_profile(profile)

    complete = True
    for document, present in growth_inputs.items():
        if present:
            st.success(f"{document.display_name} is present")
        else:
            st.error(f"Missing {document.display_name}. Return to inputs.")
            complete = False


    generate_button = st.button("Generate Growth Plan", disabled = not complete)

    if generate_button:
        output_placeholder = st.empty()
        system_prompt = growth_plan.load_system_prompt()
        user_prompt = growth_plan.build_user_prompt(profile, repo)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        with st.spinner("Creating growth plan..."):
            messages, response = asyncio.run(
                chat_handler.run_conversation(
                    messages,
                    output_placeholder,
                    max_tokens=4000,
                )
            )
        st.session_state["generated_growth_plan"] = response
