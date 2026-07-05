import os
from typing import Type, Dict
from .llm_base import LLMService
from .llm_providers import GeminiProvider, LocalOpenAIProvider

def get_llm() -> LLMService:
    """
    Factory function that reads the configuration environment and returns 
    an initialized instance of the correct LLM provider.

    This decouples the application frontend/pages from the underlying AI model 
    infrastructure, allowing seamless switching via runtime environment flags.

    Configuration:
        - Env Variable: `ACTIVE_LLM`
        - Options: 
            * 'gemini' -> Routes to GeminiProvider (Google Gen AI SDK)
            * 'vt'     -> Routes to LocalOpenAIProvider (VT Local OpenAI-compatible instance)

    :return: An initialized instance of a concrete LLMService implementation.
    :raises ValueError: If the ACTIVE_LLM variable contains an unsupported provider key.
    """
    # Read the target model selection, fallback gracefully to 'gemini' if unconfigured
    active_model = os.getenv("ACTIVE_LLM", "gemini").lower()

    # Map configuration string tokens directly to concrete class references
    providers: Dict[str, Type[LLMService]] = {
        "gemini": GeminiProvider,
        "vt": LocalOpenAIProvider
    }

    provider_class = providers.get(active_model)

    # Throw a descriptive engineering error if an invalid flag is passed in the environment
    if not provider_class:
        raise ValueError(
            f"Configuration Error: Unsupported ACTIVE_LLM value '{active_model}'. "
            f"Valid options are: {', '.join(providers.keys())}"
        )

    # Return the instantiated provider instance matching the requested type
    return provider_class()