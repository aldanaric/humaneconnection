import streamlit as st
import asyncio
from models.profile import Profile

from repositories.profile_repository import ProfileRepository

from services import growth_plan, rag

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


    use_humane_connection = st.checkbox(
        "Use Humane Connection",
        value=True,
        key=f"growth_plan_use_humane_connection_{profile.id}",
        help=(
            "When enabled, the Growth Plan uses relevant passages from the "
            "existing Humane Connection embedding index."
        ),
    )

    generate_button = st.button("Generate Growth Plan", disabled=not complete)

    if generate_button:
        output_placeholder = st.empty()
        system_prompt = growth_plan.load_system_prompt()
        user_prompt = growth_plan.build_user_prompt(profile, repo)

        if use_humane_connection:
            retrieval_query = (
                "Humane Connection guidance for an employee growth plan, including "
                "communication, accountability, diagnosis, behavioral commitments, "
                "psychological safety, personality, and manager support.\n\n"
                + user_prompt[:8000]
            )
            try:
                rag_context = rag.retrieve_context(retrieval_query, top_k=5)
            except Exception as exc:
                st.error(f"Unable to use Humane Connection RAG: {exc}")
                st.stop()

            system_prompt += (
                "\n\n## Retrieved Humane Connection guidance\n"
                "Use the following excerpts as authoritative supporting context. "
                "Apply them only where relevant to the participant's evidence. "
                "Do not invent source claims.\n\n"
                + rag_context["combined_context"]
            )

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
        st.session_state["selected_plan"] = None
