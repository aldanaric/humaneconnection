import streamlit as st
from pathlib import Path
from services import llm_config


def render_sidebar() -> None:
    show()


def _render_sidebar_layout_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] .st-key-llm_sidebar_bottom {
            position: fixed;
            bottom: 1.25rem;
            left: 1rem;
            width: 260px !important;
            max-width: 260px !important;
            height: auto !important;
            z-index: 1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _provider_label(provider_key: str) -> str:
    config = llm_config.resolve_config(provider_key)
    if config.is_ready:
        status = "ready"
    elif "API key" in config.missing_requirements:
        status = "API key required"
    else:
        status = "setup required"
    return f"{config.provider.label} - {status}"


def _sync_selected_provider() -> None:
    selected_provider = st.session_state.get(llm_config.SESSION_PROVIDER_WIDGET_KEY)
    if selected_provider:
        llm_config.set_session_provider_key(selected_provider)


def _render_llm_selector() -> None:
    current_provider = llm_config.get_session_provider_key()
    provider_keys = llm_config.provider_keys()

    if current_provider not in provider_keys:
        current_provider = provider_keys[0]

    widget_provider = st.session_state.get(llm_config.SESSION_PROVIDER_WIDGET_KEY)
    if widget_provider != current_provider:
        st.session_state[llm_config.SESSION_PROVIDER_WIDGET_KEY] = current_provider

    selected_provider = st.selectbox(
        "LLM Provider",
        provider_keys,
        index=provider_keys.index(current_provider),
        format_func=_provider_label,
        key=llm_config.SESSION_PROVIDER_WIDGET_KEY,
        on_change=_sync_selected_provider,
    )
    llm_config.set_session_provider_key(selected_provider)

    config = llm_config.resolve_config(selected_provider)

    if selected_provider == "compatible":
        custom_config = llm_config.get_custom_config()
        base_url = st.text_input(
            "Base URL",
            value=custom_config.get("base_url") or config.base_url,
            placeholder="https://your-provider.example/v1",
            key="llm_compatible_base_url",
        )
        model = st.text_input(
            "Model",
            value=custom_config.get("model") or config.model,
            placeholder="provider-model-name",
            key="llm_compatible_model",
        )
        llm_config.set_custom_config(base_url, model)
        config = llm_config.resolve_config(selected_provider)

    if config.provider.requires_api_key and not config.has_configured_api_key:
        saved_session_key = llm_config.get_session_api_key(selected_provider)
        input_key = f"llm_api_key_input_{selected_provider}"
        if saved_session_key and st.session_state.get(input_key):
            st.session_state[input_key] = ""

        api_key = st.text_input(
            f"{config.provider.label} API key",
            type="password",
            placeholder="Stored only for this session",
            key=input_key,
        )
        if api_key and api_key != saved_session_key:
            llm_config.set_session_api_key(selected_provider, api_key)
            st.rerun()

    if config.is_ready:
        st.caption(f"Using {config.provider.label}: `{config.model}`")
    else:
        missing = ", ".join(config.missing_requirements)
        st.warning(
            f"Provide {missing} to use {config.provider.label}. "
            "API keys are only kept for this session.",
            icon="⚠️",
        )


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
        _render_sidebar_layout_css()

        logo_path = Path(__file__).parent.parent.parent / "static" / "AIDDIlogopending.png"
        st.image(str(logo_path), width=300)
        st.markdown("v2026.07")
        #st.markdown(f"""
        #    <a href="/" style="color:black;text-decoration: none;">
        #        <div style="display:table;margin-left:0%;">
        #            <img src="app/static/logo.png" width="80"><span style="color: white">&nbsp;AIDDI</span>
        #            <span style="font-size: 0.8em; color: grey">&nbsp;&nbsp;v2026.06    </span>
        #        </div>
        #    </a>
        #    <br>
        #        """, unsafe_allow_html=True)

        reload_button = st.button("↪︎  Reload Page")
        if reload_button:
            st.session_state.clear()
            st.rerun()

        with st.container(key="llm_sidebar_bottom"):
            st.divider()
            if st.session_state.account is not None:
                _render_llm_selector()
