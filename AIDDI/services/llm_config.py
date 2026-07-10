import os
from dataclasses import dataclass
from typing import Dict, Optional

from dotenv import load_dotenv


load_dotenv()


SESSION_PROVIDER_KEY = "llm_active_provider"
SESSION_PROVIDER_WIDGET_KEY = "llm_selected_provider"
SESSION_API_KEYS_KEY = "llm_session_api_keys"
SESSION_CUSTOM_CONFIG_KEY = "llm_custom_provider_config"


@dataclass(frozen=True)
class ProviderConfig:
    key: str
    label: str
    default_base_url: str
    default_model: str
    requires_api_key: bool = True


@dataclass(frozen=True)
class ResolvedLLMConfig:
    provider: ProviderConfig
    api_key: Optional[str]
    base_url: str
    model: str
    has_configured_api_key: bool
    has_session_api_key: bool

    @property
    def is_ready(self) -> bool:
        return not self.missing_requirements

    @property
    def missing_requirements(self) -> list[str]:
        missing = []
        if self.provider.requires_api_key and not self.api_key:
            missing.append("API key")
        if not self.base_url:
            missing.append("base URL")
        if not self.model:
            missing.append("model")
        return missing


SUPPORTED_PROVIDERS: Dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        key="openai",
        label="OpenAI",
        default_base_url="https://api.openai.com/v1",
        default_model="gpt-4.1-mini",
    ),
    "gemini": ProviderConfig(
        key="gemini",
        label="Google Gemini",
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.5-flash",
    ),
    "openrouter": ProviderConfig(
        key="openrouter",
        label="OpenRouter",
        default_base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4.1-mini",
    ),
    "compatible": ProviderConfig(
        key="compatible",
        label="Other OpenAI-compatible endpoint",
        default_base_url="",
        default_model="",
    ),
}


def provider_keys() -> list[str]:
    return list(SUPPORTED_PROVIDERS.keys())


def get_provider(provider_key: Optional[str]) -> ProviderConfig:
    if provider_key in SUPPORTED_PROVIDERS:
        return SUPPORTED_PROVIDERS[provider_key]
    return SUPPORTED_PROVIDERS["openai"]


def get_default_provider_key() -> str:
    configured_provider = os.getenv("LLM_PROVIDER", "").lower()
    if configured_provider in SUPPORTED_PROVIDERS:
        return configured_provider
    return "openai"


def env_name(provider_key: str, setting: str) -> str:
    return f"LLM_{provider_key.upper()}_{setting}"


def get_env_value(provider_key: str, setting: str) -> Optional[str]:
    provider_value = os.getenv(env_name(provider_key, setting))
    if provider_value:
        return provider_value

    legacy_provider = os.getenv("LLM_PROVIDER", "").lower()
    if legacy_provider == provider_key:
        return os.getenv(f"LLM_{setting}")

    return None


def get_session_state():
    try:
        import streamlit as st

        return st.session_state
    except Exception:
        return None


def get_session_provider_key() -> str:
    session_state = get_session_state()
    if session_state is not None:
        provider_key = session_state.get(SESSION_PROVIDER_KEY)
        if provider_key in SUPPORTED_PROVIDERS:
            return provider_key

        provider_key = session_state.get(SESSION_PROVIDER_WIDGET_KEY)
        if provider_key in SUPPORTED_PROVIDERS:
            session_state[SESSION_PROVIDER_KEY] = provider_key
            return provider_key
    return get_default_provider_key()


def set_session_provider_key(provider_key: str) -> None:
    session_state = get_session_state()
    if session_state is None or provider_key not in SUPPORTED_PROVIDERS:
        return

    session_state[SESSION_PROVIDER_KEY] = provider_key


def get_session_api_key(provider_key: str) -> Optional[str]:
    session_state = get_session_state()
    if session_state is None:
        return None

    api_keys = session_state.get(SESSION_API_KEYS_KEY, {})
    return api_keys.get(provider_key)


def set_session_api_key(provider_key: str, api_key: str) -> None:
    session_state = get_session_state()
    if session_state is None:
        return

    api_keys = dict(session_state.get(SESSION_API_KEYS_KEY, {}))
    if api_key:
        api_keys[provider_key] = api_key
    else:
        api_keys.pop(provider_key, None)
    session_state[SESSION_API_KEYS_KEY] = api_keys


def get_custom_config() -> dict:
    session_state = get_session_state()
    if session_state is None:
        return {}
    return dict(session_state.get(SESSION_CUSTOM_CONFIG_KEY, {}))


def set_custom_config(base_url: str, model: str) -> None:
    session_state = get_session_state()
    if session_state is None:
        return
    session_state[SESSION_CUSTOM_CONFIG_KEY] = {
        "base_url": base_url.strip(),
        "model": model.strip(),
    }


def resolve_config(provider_key: Optional[str] = None) -> ResolvedLLMConfig:
    provider = get_provider(provider_key or get_session_provider_key())
    custom_config = get_custom_config() if provider.key == "compatible" else {}

    configured_api_key = get_env_value(provider.key, "API_KEY")
    session_api_key = get_session_api_key(provider.key)
    api_key = configured_api_key or session_api_key

    base_url = (
        custom_config.get("base_url")
        or get_env_value(provider.key, "BASE_URL")
        or provider.default_base_url
    )
    model = (
        custom_config.get("model")
        or get_env_value(provider.key, "MODEL")
        or provider.default_model
    )

    if not provider.requires_api_key and not api_key:
        api_key = "not-needed"

    return ResolvedLLMConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        has_configured_api_key=bool(configured_api_key),
        has_session_api_key=bool(session_api_key),
    )
