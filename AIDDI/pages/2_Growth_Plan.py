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

if "observation_rows" not in st.session_state:
    st.session_state.observation_rows = 1

# --- SECTION 1: File Upload & Profile Creation ---
with st.expander("➕ Add New Profile"):
    with st.form('input'):
        folder_name = st.text_input("Input the person name for these files (Last, First)")
        personality = st.file_uploader(
            "Personality Assessment",
            type=["md", "pdf"])
        job_functions = st.file_uploader(
            "Job Functions",
            type=["md", "pdf"])
        observations = st.file_uploader(
            "Observations",
            type=["md", 'pdf'])
        submit = st.form_submit_button("Add/Update Profile files")


if submit:
    try:
        folder, existed = growth_plan.create_person_folder(folder_name)
        last, first = growth_plan.split_last_first(folder.name)
        growth_plan.save_uploaded_file(
            personality,
            folder / f"2_Personality_Assessment_{first}_{last}.md"
        )
        growth_plan.save_uploaded_file(
            job_functions,
            folder / f"Job_Functions_{first}_{last}.md"
        )
        growth_plan.save_uploaded_file(
            observations,
            folder / f"Observations_{first}_{last}.md"
        )
        if existed:
            st.info("Existing profile found. Uploaded files overwrite existing files")
        else:
            st.success(f"Folder '{folder.name}' created.")

    except ValueError as e:
        st.error(str(e))

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
        st.success(f"{label}: `{path.name}`")
    else:
        st.error(f"Missing {label}")

manual_inputs = {}

if "Job Functions" in missing_files:
    manual_inputs["Job Title"] = st.text_input("Job Title")
    manual_inputs["Job Functions"] = st.text_area("Job functions",
                                                  height=200
                                                  )
if "Observations" in missing_files:
    manual_inputs["Observations"] = []
    st.subheader("Areas for Improvement")

    for i in range(st.session_state.observation_rows):
        area = st.text_input(f"**Area {i + 1}**:")
        col1, col2 = st.columns(2)
        with col1:
            observation = st.text_area(
                "Observation",
                key=f"observation_{i}",
                height=100,
            )
        with col2:
            impact = st.text_area(
                "Impact",
                key=f"impact_{i}",
                height=100
            )
        manual_inputs["Observations"].append(
            {
                "area": area,
                "observation": observation,
                "impact": impact
            }
        )

    if st.button("➕ Add another observation"):
        st.session_state.observation_rows +=1
        st.rerun()

create_button = st.button(
    "Create Growth Plan",
    type="primary"
)

if create_button:
    output_placeholder = st.empty()

    try:
        folder = growth_plan.INPUT_DIR / selected_folder
        last, first = growth_plan.split_last_first(selected_folder)

        if (
            "Job Functions" in manual_inputs and
            manual_inputs["Job Functions"].strip()
        ):
            content = f"""# Job Title

            {manual_inputs["Job Title"]}

            #Job Functions

            {manual_inputs["Job Functions"]}
            """
            (folder / f"Job_Functions_{first}_{last}.md").write_text(
                content, encoding="utf-8",
            )

        if "Observations" in manual_inputs:
            sections = []
            for pair in manual_inputs["Observations"]:
                if not pair["area"].strip():
                    continue
                sections.append(
                    f"""## Area
                    {pair["area"]}
                    ### Observation
                    {pair["observation"]}
                    ### Impact
                    {pair["impact"]}
                    """
                )
            if not sections:
                st.error("Please enter at least one observation.")
                st.stope()

            observations_md = "\n\n".join(sections)
            (folder / f"Observations_{first}_{last}.md").write_text(
                observations_md, encoding="utf-8",
            )

        is_valid, required_files, missing_files = growth_plan.validate_inputs(
            selected_folder
        )
        if not is_valid:
            st.error(f"Still missing: {', '.join(missing_files)}")
            st.stop()
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
