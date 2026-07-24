from pathlib import Path

import streamlit as st

from services import saved_prompts

logo = Path(__file__).resolve().parents[1] / "static" / "AIDDIlogopendingsquare.png"

st.set_page_config(
    page_title="Saved Prompts",
    page_icon=logo,
    layout="wide",
)

st.header("Saved Prompts")
st.write(
    "Browse the prompts used across AIDDI features. "
    "This is a UI prototype — prompts are still loaded from the current "
    "filesystem / code sources. A shared database-backed store will replace "
    "this later."
)

# Sidebar is rendered by Home.py

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
            st.caption(f"{item.feature} · `{item.source}`")
        with col_open:
            open_clicked = st.button(
                "View",
                key=f"view_{item.id}",
                use_container_width=True,
            )

        if open_clicked:
            st.session_state["saved_prompt_selected_id"] = item.id

selected_id = st.session_state.get("saved_prompt_selected_id")
selected = (
    saved_prompts.get_saved_prompt(selected_id) if selected_id else None
)

# Keep selection valid when the filter changes.
if selected is not None and selected.id not in {item.id for item in catalog}:
    selected = catalog[0]
    st.session_state["saved_prompt_selected_id"] = selected.id
elif selected is None:
    selected = catalog[0]
    st.session_state["saved_prompt_selected_id"] = selected.id

st.divider()
st.subheader(f"{selected.feature}: {selected.name}")
st.caption(f"Source: `{selected.source}`")

system_tab, format_tab = st.tabs(["System prompt", "Output format"])

with system_tab:
    st.text_area(
        "System prompt",
        value=selected.system_prompt,
        height=360,
        disabled=True,
        label_visibility="collapsed",
    )

with format_tab:
    if selected.output_format.strip():
        st.text_area(
            "Output format",
            value=selected.output_format,
            height=360,
            disabled=True,
            label_visibility="collapsed",
        )
    else:
        st.caption("This prompt does not define a separate output-format file.")
