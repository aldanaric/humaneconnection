import streamlit as st
from pathlib import Path

# Assuming these will exist in your project structure
from ui.components import diagnostic_inputs
from ui.components import diagnostic_generate
from ui.components import diagnostic_output

logo = Path(__file__).resolve().parent / "static" / "AIDDIlogopendingsquare.png"

st.set_page_config(
    page_title="Diagnostic Intelligence Summary",
    page_icon=logo,
    layout="wide"
)

st.header("Diagnostic Intelligence Summary")

# Dummy list for UI purposes
options = ["--Select a client/profile--", "Company ABC Inc.", "+ Add new client"]

selected = st.selectbox("Select Client / Profile", options)

if selected == "+ Add new client":
    st.subheader("Create new Client Profile:")
    client_name = st.text_input("Client/Company Name")
    contact_name = st.text_input("Primary Contact")
    
    if st.button("Create profile"):
        st.success(f"Created profile for {client_name}")
        st.rerun()

elif selected == "--Select a client/profile--":
    st.stop()

# --- Tabs Setup ---
inputs_tab, generate_tab, output_tab = st.tabs(
    ["Inputs", "Generate", "Outputs"]
)

with inputs_tab:
    diagnostic_inputs.render(selected)
    # st.write("*(Input Component Placeholder)*")

with generate_tab:
    diagnostic_generate.render(selected)
    # st.write("*(Generate Component Placeholder)*")

with output_tab:
    diagnostic_output.render(selected)
    # st.write("*(Output Component Placeholder)*")