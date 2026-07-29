"""Run configuration and generation for Team Diagnostics."""
from __future__ import annotations

import asyncio

import streamlit as st

from models.account import Account
from repositories.profile_repository import ProfileRepository
from services import rag
from ui.interactions import chat_handler
from ui.components import team_diagnostics_output
import services.team_diagnostics as team_diagnostics


def render(account: Account, selected_team: str, repo: ProfileRepository) -> str:
    """Render generate controls. Returns the selected prompt template name."""
    member_statuses = team_diagnostics.team_member_statuses(
        account,
        selected_team,
        repo,
    )

    templates = team_diagnostics.list_prompt_templates()
    if not templates:
        st.error(
            "No Team Diagnostics prompt templates found. "
            "An admin can create them on the Saved Prompts page."
        )
        st.stop()

    if "selected_template" not in st.session_state:
        st.session_state.selected_template = templates[0]
    if st.session_state.selected_template not in templates:
        st.session_state.selected_template = templates[0]

    selected_template = st.selectbox(
        "Prompt template",
        templates,
        index=templates.index(st.session_state.selected_template),
        help="Prompt templates are managed by admins on the Saved Prompts page.",
    )
    st.session_state.selected_template = selected_template

    st.subheader("Run configuration")

    col_audience, col_outputs = st.columns(2)

    with col_audience:
        audience = st.radio(
            "Audience",
            team_diagnostics.AUDIENCES,
            index=0,
            help="Facilitator is the default for training and breakout sessions.",
        )

    with col_outputs:
        selected_outputs = st.multiselect(
            "Outputs to generate",
            team_diagnostics.OUTPUT_OPTIONS,
            default=list(team_diagnostics.OUTPUT_OPTIONS),
        )

    is_valid, _, issues = team_diagnostics.validate_team(
        account,
        selected_team,
        repo,
    )

    if issues:
        for issue in issues:
            st.error(issue)
    else:
        st.success(f"{len(member_statuses)} members ready.")

    use_humane_connection = st.checkbox(
        "Use Humane Connection",
        value=True,
        key=f"team_diagnostics_use_humane_connection_{selected_team}",
        help=(
            "When enabled, Team Diagnostics uses relevant passages from the "
            "existing Humane Connection embedding index."
        ),
    )

    generate = st.button(
        "Generate Team Diagnostics",
        type="primary",
        disabled=not is_valid or not selected_outputs,
    )

    if not generate:
        return selected_template

    output_placeholder = st.empty()
    try:
        system_message = team_diagnostics.build_system_message(selected_template)
        user_prompt = team_diagnostics.build_user_prompt(
            account,
            selected_team,
            audience,
            selected_outputs,
            repo,
        )

        if use_humane_connection:
            retrieval_query = (
                "Humane Connection guidance for team diagnostics, including "
                "team dynamics, communication styles, collaboration, conflict, "
                "psychological safety, personality patterns, and facilitator coaching.\n\n"
                + user_prompt[:8000]
            )
            try:
                rag_context = rag.retrieve_context(retrieval_query, top_k=5)
            except Exception as exc:
                st.error(f"Unable to use Humane Connection RAG: {exc}")
                st.stop()

            system_message += (
                "\n\n## Retrieved Humane Connection guidance\n"
                "Use the following excerpts as authoritative supporting context. "
                "Apply them only where relevant to the team's evidence. "
                "Do not invent source claims. Preserve the requested Team Diagnostics "
                "output format and headings.\n\n"
                + rag_context["combined_context"]
            )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt},
        ]

        with st.spinner("Generating team diagnostics..."):
            _, response = asyncio.run(
                chat_handler.run_conversation(
                    messages,
                    output_placeholder,
                    max_tokens=8000,
                )
            )

        report = team_diagnostics.save_team_diagnostics(
            account,
            selected_team,
            response,
            template_name=selected_template,
            audience=audience,
            requested_outputs=selected_outputs,
            used_humane_connection=use_humane_connection,
        )
        team_diagnostics_output.set_current_report(selected_team, report)
        st.success(f"Saved report `{report.title}`.")
        st.info("Open the **Output** tab to review and edit the packet.")
    except Exception as exc:
        st.exception(exc)

    return selected_template
