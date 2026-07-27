from pathlib import Path

import streamlit as st

from models.access_level import AccessLevel
from services import saved_prompts

logo = Path(__file__).resolve().parents[1] / "static" / "AIDDIlogopendingsquare.png"

st.set_page_config(
    page_title="Saved Prompts",
    page_icon=logo,
    layout="wide",
)

st.header("Saved Prompts")
st.write(
    "Admin prompt management across AIDDI features. "
    "Filesystem-backed for now — a shared database store will replace this later."
)

# Sidebar is rendered by Home.py
account = st.session_state.get("account")
if account is None or account.access_level != AccessLevel.ADMIN:
    st.error("Saved Prompts is available to admins only.")
    st.stop()

feature_filter = st.selectbox(
    "Feature",
    ["All", *saved_prompts.FEATURES],
)

catalog = saved_prompts.list_saved_prompts(
    None if feature_filter == "All" else feature_filter
)

if not catalog:
    st.info("No saved prompts found for this filter.")
    st.stop()

st.subheader("Prompt library")
st.caption(f"{len(catalog)} prompt(s)")

for item in catalog:
    with st.container(border=True):
        col_meta, col_open = st.columns([4, 1])
        with col_meta:
            st.markdown(f"**{item.name}**")
            editable_label = "editable" if saved_prompts.is_editable(item) else "read-only"
            st.caption(f"{item.feature} · {editable_label} · `{item.source}`")
        with col_open:
            if st.button("Open", key=f"view_{item.id}", use_container_width=True):
                st.session_state["saved_prompt_selected_id"] = item.id

selected_id = st.session_state.get("saved_prompt_selected_id")
selected = saved_prompts.get_saved_prompt(selected_id) if selected_id else None

if selected is not None and selected.id not in {item.id for item in catalog}:
    selected = catalog[0]
    st.session_state["saved_prompt_selected_id"] = selected.id
elif selected is None:
    selected = catalog[0]
    st.session_state["saved_prompt_selected_id"] = selected.id

st.divider()
st.subheader(f"{selected.feature}: {selected.name}")
st.caption(f"Source: `{selected.source}`")

editable = saved_prompts.is_editable(selected)
system_tab, format_tab = st.tabs(["System prompt", "Output format"])

with system_tab:
    system_text = st.text_area(
        "System prompt",
        value=selected.system_prompt,
        height=360,
        disabled=not editable,
        key=f"system_edit_{selected.id}",
        label_visibility="collapsed",
    )

with format_tab:
    if selected.feature == "Team Diagnostics" or selected.output_format.strip():
        format_text = st.text_area(
            "Output format",
            value=selected.output_format,
            height=360,
            disabled=not editable,
            key=f"format_edit_{selected.id}",
            label_visibility="collapsed",
        )
    else:
        format_text = ""
        st.caption("This prompt does not define a separate output-format file.")

if editable:
    col_save, col_save_as = st.columns(2)
    with col_save:
        if st.button("Save changes", type="primary"):
            try:
                saved_prompts.save_prompt_content(
                    selected.id,
                    system_text,
                    format_text,
                )
                st.success(f"Saved `{selected.name}`")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with col_save_as:
        if selected.feature == "Team Diagnostics":
            with st.form("save_as_td_template"):
                new_name = st.text_input(
                    "Save Team Diagnostics template as",
                    placeholder="e.g. ignh_facilitator_v2",
                )
                submitted = st.form_submit_button("Save as new")
            if submitted:
                try:
                    created = saved_prompts.create_team_diagnostics_template(
                        new_name,
                        system_text,
                        format_text,
                    )
                    st.session_state["saved_prompt_selected_id"] = created.id
                    st.success(f"Created `{created.name}`")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
else:
    st.info("Quick Chat prompts are defined in code and are read-only on this page.")
