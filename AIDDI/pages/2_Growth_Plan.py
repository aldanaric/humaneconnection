import asyncio

import streamlit as st

from ui.components import sidebar
from ui.interactions import chat_handler
import services.growth_plan as growth_plan
import services.llm

st.set_page_config(
    page_title="Growth Plan",
    page_icon="🌱",
    layout="wide"
)

st.header("Growth Plan")

sidebar.render_sidebar()

st.markdown(
    "Select a person folder from `data/GrowthPlan`. "
    "The folder must be named `Last_First` and contain the required markdown inputs."
)

person_folders = growth_plan.list_person_folders()

if not person_folders:
    st.warning("No Growth Plan person folders found in `data/GrowthPlan`.")
    st.stop()

selected_folder = st.selectbox("Select person", person_folders)

is_valid, required_files, missing_files = growth_plan.validate_inputs(selected_folder)

st.subheader("Required inputs")
for label, path in required_files.items():
    if path.exists():
        st.success(f"{label}: `{path}`")
    else:
        st.error(f"Missing {label}: `{path}`")

create_button = st.button(
    "Create Growth Plan",
    type="primary",
    disabled=not is_valid,
)

if create_button:
    output_placeholder = st.empty()

    try:
        system_prompt = growth_plan.load_system_prompt()
        user_prompt = growth_plan.build_user_prompt(selected_folder)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        with st.spinner("Creating growth plan..."):
            _, response = asyncio.run(
                chat_handler.run_conversation(
                    messages,
                    output_placeholder,
                    max_tokens=4000,
                )
            )

        saved_path = growth_plan.save_growth_plan(selected_folder, response)
        st.success(f"Growth Plan saved to `{saved_path}`")
        st.download_button(
            "Download Growth Plan",
            data=response,
            file_name=saved_path.name,
            mime="text/markdown",
        )

    except Exception as exc:
        st.exception(exc)
