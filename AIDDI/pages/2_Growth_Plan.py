import asyncio
from pathlib import Path

import streamlit as st

from ui.components import sidebar
from ui.interactions import chat_handler
import services.growth_plan as growth_plan
from repositories.profile_repository import ProfileRepository
from models.document_type import DocumentType

from ui.components import growth_plan_inputs
from ui.components import generate_growth_plan
from ui.components import growth_plan_output
from ui.components import profile_picker

from models.account import Account
from repositories.account_repository import AccountRepository

logo = Path(__file__).resolve().parents[1] / "static" / "AIDDIlogopendingsquare.png"

st.set_page_config(
    page_title="Growth Plan",
    page_icon=logo,
    layout="wide"
)

st.header("Growth Plan")

#sidebar.render_sidebar()

account = st.session_state.get("account")

repo = ProfileRepository(account.id)

NO_GENERATED_PLAN = "No plan has been generated this session"

st.markdown("Select a company, then a profile to generate a growth plan for:")

selected_profile = ""
profiles = repo.list_profiles()
companies = profile_picker.list_companies(profiles)

company_options = [profile_picker.SELECT_COMPANY, *companies]
selected_company = st.selectbox(
    "Company",
    company_options,
    key="growth_plan_company",
)

if selected_company == profile_picker.SELECT_COMPANY:
    st.info("Choose a company to see its profiles.")
    # Still allow creating a profile without filtering.
    if st.button("Create new profile", key="growth_plan_create_without_company"):
        st.session_state["growth_plan_show_create"] = True

    if st.session_state.get("growth_plan_show_create"):
        st.subheader("Create new Profile:")
        first_name = st.text_input("First Name", key="gp_create_first")
        last_name = st.text_input("Last Name", key="gp_create_last")
        company = st.text_input("Employer", key="gp_create_company")
        if st.button("Create profile", key="gp_create_submit"):
            profile = repo.create_profile(first_name, last_name, company)
            st.session_state.pop("growth_plan_show_create", None)
            st.success(f"Created profile for {profile.display_name}")
            st.rerun()
    st.stop()

filtered_profiles = profile_picker.profiles_for_company(profiles, selected_company)

person_options = [
    profile_picker.SELECT_PROFILE,
    *filtered_profiles,
    "+ Add new profile",
]

selected = st.selectbox(
    "Select Person",
    person_options,
    format_func=lambda x: x.display_name if hasattr(x, "display_name") else x,
    key=f"growth_plan_person_{selected_company}",
)

if selected == "+ Add new profile":
    st.subheader("Create new Profile:")

    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    company = st.text_input("Employer", value=(
        "" if selected_company == profile_picker.UNASSIGNED_COMPANY else selected_company
    ))

    if st.button("Create profile"):
        profile = repo.create_profile(first_name, last_name, company)
        st.success(f"Created profile for {profile.display_name}")
        st.rerun()
    st.stop()

elif selected == profile_picker.SELECT_PROFILE:
    st.stop()

else:
    selected_profile = selected

if not selected_profile:
    st.stop()

if (
    "current_profile_id" not in st.session_state
    or st.session_state.current_profile_id != selected_profile.id
):
    st.session_state.current_profile_id = selected_profile.id
    st.session_state.generated_growth_plan = NO_GENERATED_PLAN
    st.session_state.current_plan = None

inputs_tab, generate_tab, output_tab = st.tabs(
    ["Inputs", "Generate", "Outputs"]
)

with inputs_tab:
    growth_plan_inputs.render(selected_profile, repo)

with generate_tab:
    generate_growth_plan.render(selected_profile, repo)

with output_tab:
    growth_plan_output.render(selected_profile, repo, NO_GENERATED_PLAN)




# --- SECTION 1: File Upload & Profile Creation ---
# with st.expander("➕ Add New Profile"):
#     with st.form('input'):
#         folder_name = st.text_input("Input the person name for these files (Last, First)")
#         personality = st.file_uploader(
#             "Personality Assessment",
#             type=["md", "pdf"])
#         job_functions = st.file_uploader(
#             "Job Functions",
#             type=["md", "pdf"])
#         observations = st.file_uploader(
#             "Observations",
#             type=["md", 'pdf'])
#         submit = st.form_submit_button("Add/Update Profile files")
#
#
# if submit:
#     try:
#         folder, existed = growth_plan.create_person_folder(folder_name)
#         last, first = growth_plan.split_last_first(folder.name)
#         growth_plan.save_uploaded_file(
#             personality,
#             folder / f"2_Personality_Assessment_{first}_{last}.md"
#         )
#         growth_plan.save_uploaded_file(
#             job_functions,
#             folder / f"Job_Functions_{first}_{last}.md"
#         )
#         growth_plan.save_uploaded_file(
#             observations,
#             folder / f"Observations_{first}_{last}.md"
#         )
#         if existed:
#             st.info("Existing profile found. Uploaded files overwrite existing files")
#         else:
#             st.success(f"Folder '{folder.name}' created.")
#
#     except ValueError as e:
#         st.error(str(e))
#
#
# # --- SECTION 2: Profile Selection & Validation ---
# st.markdown(
#     "Select a person folder from `data/GrowthPlan`. "
#     "The folder must be named `Last_First` and contain the required markdown inputs."
# )
#
# person_folders = growth_plan.list_person_folders()
#
# if not person_folders:
#     st.warning("No Growth Plan person folders found in `data/GrowthPlan`.")
#     st.stop()
#
# selected_folder = st.selectbox("Select person", person_folders)
# is_valid, required_files, missing_files = growth_plan.validate_inputs(selected_folder)
#
# st.subheader("Required inputs")
# for label, path in required_files.items():
#     if path.exists():
#         st.success(f"{label}: `{path.name}`")
#     else:
#         st.error(f"Missing {label}")
#
# # Provide manual text areas if files are missing
# manual_inputs = {}
#
# if "Job Functions" in missing_files:
#     manual_inputs["Job Title"] = st.text_input("Job Title")
#     manual_inputs["Job Functions"] = st.text_area("Job functions",
#                                                   height=200
#                                                   )
# if "Observations" in missing_files:
#     manual_inputs["Observations"] = []
#     st.subheader("Areas for Improvement")
#
#     for i in range(st.session_state.observation_rows):
#         area = st.text_input(f"**Area {i + 1}**:")
#         col1, col2 = st.columns(2)
#         with col1:
#             observation = st.text_area(
#                 "Observation",
#                 key=f"observation_{i}",
#                 height=100,
#             )
#         with col2:
#             impact = st.text_area(
#                 "Impact",
#                 key=f"impact_{i}",
#                 height=100
#             )
#         manual_inputs["Observations"].append(
#             {
#                 "area": area,
#                 "observation": observation,
#                 "impact": impact
#             }
#         )
#
#     if st.button("➕ Add another observation"):
#         st.session_state.observation_rows +=1
#         st.rerun()
#
# create_button = st.button("Create Growth Plan", type="primary")
#
#
# # --- SECTION 3: Plan Generation ---
# if create_button:
#     output_placeholder = st.empty()
#
#     try:
#         folder = growth_plan.INPUT_DIR / selected_folder
#         last, first = growth_plan.split_last_first(selected_folder)
#
#         if (
#             "Job Functions" in manual_inputs and
#             manual_inputs["Job Functions"].strip()
#         ):
#             content = f"""# Job Title
#
#             {manual_inputs["Job Title"]}
#
#             #Job Functions
#
#             {manual_inputs["Job Functions"]}
#             """
#             (folder / f"Job_Functions_{first}_{last}.md").write_text(
#                 content, encoding="utf-8",
#             )
#
#         if "Observations" in manual_inputs:
#             sections = []
#             for pair in manual_inputs["Observations"]:
#                 if not pair["area"].strip():
#                     continue
#                 sections.append(
#                     f"""## Area
#                     {pair["area"]}
#                     ### Observation
#                     {pair["observation"]}
#                     ### Impact
#                     {pair["impact"]}
#                     """
#                 )
#             if not sections:
#                 st.error("Please enter at least one observation.")
#                 st.stop()
#
#             observations_md = "\n\n".join(sections)
#             (folder / f"Observations_{first}_{last}.md").write_text(
#                 observations_md, encoding="utf-8",
#             )
#
#         is_valid, required_files, missing_files = growth_plan.validate_inputs(
#             selected_folder
#         )
#         if not is_valid:
#             st.error(f"Still missing: {', '.join(missing_files)}")
#             st.stop()
#
#         # Build the prompt array
#         system_prompt = growth_plan.load_system_prompt()
#         user_prompt = growth_plan.build_user_prompt(selected_folder)
#         messages = [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt},
#         ]
#
#         # 2. NEW ARCHITECTURE: Fetch the active LLM provider
#         provider = get_llm()
#
#         # 3. NEW ARCHITECTURE: Define the async streaming block inline
#         async def generate_plan():
#             full_response = ""
#             async for chunk in provider.converse(messages, max_tokens=4000):
#                 full_response += chunk
#                 output_placeholder.markdown(full_response + "▌")
#             output_placeholder.markdown(full_response)
#             return full_response
#
#         # Execute the stream
#         with st.spinner("Creating growth plan..."):
#             response = asyncio.run(generate_plan())
#
#         # Save and Download outputs
#         saved_path = growth_plan.save_growth_plan(selected_folder, response)
#         st.success(f"Growth Plan saved to `{saved_path}`")
#         st.download_button(
#             "Download Growth Plan",
#             data=response,
#             file_name=saved_path.name,
#             mime="text/markdown",
#         )
#
#     except Exception as exc:
#         st.exception(exc)
