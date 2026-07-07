import asyncio

import streamlit as st

from ui.components import sidebar
from ui.interactions import chat_handler
import services.team_diagnostics as team_diagnostics

st.set_page_config(
    page_title="Team Diagnostics",
    page_icon="🧭",
    layout="wide",
)

st.header("Team Diagnostics")
st.write(
    "Upload team assessments, choose a saved prompt, and generate a facilitator packet."
)

sidebar.render_sidebar()
team_diagnostics.init_prompt_templates()

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
st.subheader("Prompt template")

templates = team_diagnostics.list_prompt_templates()
if not templates:
    st.error("No prompt templates found.")
    st.stop()

if "selected_template" not in st.session_state:
    st.session_state.selected_template = templates[0]

selected_template = st.selectbox(
    "Saved prompt",
    templates,
    index=templates.index(st.session_state.selected_template)
    if st.session_state.selected_template in templates
    else 0,
)
st.session_state.selected_template = selected_template

template = team_diagnostics.load_prompt_template(selected_template)

with st.expander("Edit prompt template", expanded=False):
    system_prompt_text = st.text_area(
        "System prompt",
        value=template["system_prompt"],
        height=220,
        key=f"system_{selected_template}",
    )
    output_format_text = st.text_area(
        "Output format",
        value=template["output_format"],
        height=220,
        key=f"output_{selected_template}",
    )

    col_save, col_save_as = st.columns(2)
    with col_save:
        if st.button("Save changes", key="save_template"):
            team_diagnostics.save_prompt_template(
                selected_template,
                system_prompt_text,
                output_format_text,
            )
            st.success(f"Saved `{selected_template}`")
            st.rerun()
    with col_save_as:
        with st.form("save_as"):
            new_name = st.text_input("Save as new template", placeholder="e.g. ignh_facilitator_v2")
            save_as = st.form_submit_button("Save as new")
        if save_as:
            try:
                saved_name = team_diagnostics.save_prompt_template(
                    new_name,
                    system_prompt_text,
                    output_format_text,
                )
                st.session_state.selected_template = saved_name
                st.success(f"Created `{saved_name}`")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

# ---------------------------------------------------------------------------
# Add / update team
# ---------------------------------------------------------------------------
with st.expander("➕ Add New Team"):
    with st.form("add_team"):
        team_name_input = st.text_input(
            "Team name",
            placeholder="e.g. IGNH Leadership",
        )
        create_team = st.form_submit_button("Create Team")

if create_team:
    try:
        folder, existed = team_diagnostics.create_team_folder(team_name_input)
        if existed:
            st.info(f"Team `{folder.name}` already exists.")
        else:
            st.success(f"Team `{folder.name}` created.")
            st.rerun()
    except ValueError as exc:
        st.error(str(exc))

# ---------------------------------------------------------------------------
# Select team
# ---------------------------------------------------------------------------
teams = team_diagnostics.list_teams()

if not teams:
    st.warning("No teams found. Create a team above to get started.")
    st.stop()

selected_team = st.selectbox("Select team", teams)

# ---------------------------------------------------------------------------
# Team members
# ---------------------------------------------------------------------------
st.subheader("Team members")

member_statuses = team_diagnostics.team_member_statuses(selected_team)

if not member_statuses:
    st.info("No members on this team yet. Add members below.")
else:
    for status in member_statuses:
        if status["has_personality"]:
            st.success(f"{status['display_name']}: `{status['personality_path'].name}`")
        else:
            st.error(f"{status['display_name']}: Missing personality assessment")

with st.expander("➕ Add / Update Member"):
    with st.form("add_member"):
        member_name_input = st.text_input(
            "Member name (Last, First)",
            placeholder="e.g. Reyes, Christian",
        )
        personality_upload = st.file_uploader("Personality Assessment", type="md")
        add_member = st.form_submit_button("Add/Update Member")

if add_member:
    try:
        member_folder, existed = team_diagnostics.create_member_folder(
            selected_team,
            member_name_input,
        )
        last, first = team_diagnostics.split_last_first(member_folder.name)
        destination = member_folder / f"Personality_Assessment_{first}_{last}.md"
        team_diagnostics.save_uploaded_file(personality_upload, destination)

        if personality_upload is None:
            st.warning("Member folder created, but no assessment was uploaded.")
        else:
            st.success(f"Updated `{first} {last}` on `{selected_team}`.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

# ---------------------------------------------------------------------------
# Run configuration
# ---------------------------------------------------------------------------
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

is_valid, _, issues = team_diagnostics.validate_team(selected_team)

if issues:
    for issue in issues:
        st.error(issue)
else:
    st.success(f"{len(member_statuses)} members ready.")

generate = st.button(
    "Generate Team Diagnostics",
    type="primary",
    disabled=not is_valid or not selected_outputs,
)

if generate:
    output_placeholder = st.empty()
    try:
        system_message = team_diagnostics.build_system_message(selected_template)
        user_prompt = team_diagnostics.build_user_prompt(
            selected_team,
            audience,
            selected_outputs,
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

        saved_path = team_diagnostics.save_team_diagnostics(
            selected_team,
            response,
            template_name=selected_template,
        )
        st.session_state[f"last_output_{selected_team}"] = response
        st.success(f"Saved to `{saved_path}`")
    except Exception as exc:
        st.exception(exc)

# ---------------------------------------------------------------------------
# Generated output
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Generated output")

saved_output = team_diagnostics.load_saved_output(selected_team)
display_output = st.session_state.get(f"last_output_{selected_team}") or saved_output

if display_output:
    st.download_button(
        "Download packet",
        data=display_output,
        file_name=f"TeamDiagnostics_{selected_team}.md",
        mime="text/markdown",
    )
    st.markdown(display_output)
else:
    st.caption("Generate a packet to see output here.")
