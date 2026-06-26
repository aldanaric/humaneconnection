import streamlit as st


def render_sidebar() -> None:   
    show()  
def show() -> None:
    """
    Displays the sidebar with the AIDDI logo and a reload button.

    This function creates a consistent sidebar across all pages of the application,
    including the AIDDI logo with version number and a reload button that clears
    the session state and reruns the application.

    Returns:
        None
    """
    with st.sidebar:
        st.markdown(f"""
            <a href="/" style="color:black;text-decoration: none;">
                <div style="display:table;margin-left:0%;">
                    <img src="app/static/logo.png" width="80"><span style="color: white">&nbsp;AIDDI</span>
                    <span style="font-size: 0.8em; color: grey">&nbsp;&nbsp;v2026.06    </span>
                </div>
            </a>
            <br>
                """, unsafe_allow_html=True)

        reload_button = st.button("↪︎  Reload Page")
        if reload_button:
            st.session_state.clear()
            st.rerun()
