import traceback

from typing import List, Dict, Tuple, AsyncGenerator

from openai import AsyncOpenAI, OpenAI, OpenAIError

from services.llm_config import resolve_config


# Roles the chat-completions API actually understands. The app also stores
# UI-only "evidence" entries (RAG citations, with raw image bytes attached)
# in the same session_state.messages list used as conversation history, so
# anything sent to the LLM has to be filtered down to this set first.
_API_ROLES = {"system", "user", "assistant", "tool"}


def _sanitize_messages_for_api(messages: List[Dict]) -> List[Dict[str, str]]:
    """Return a clean copy of `messages` safe to JSON-serialize and send to
    an OpenAI-compatible chat API: only recognized roles, only `role` and
    `content`, and content coerced to a string (drops things like raw
    `image_data` bytes that the UI attaches to "evidence" entries).
    """
    sanitized: List[Dict[str, str]] = []
    for message in messages:
        role = message.get("role")
        if role not in _API_ROLES:
            continue
        content = message.get("content", "")
        if not isinstance(content, str):
            content = "" if content is None else str(content)
        sanitized.append({"role": role, "content": content})
    return sanitized


def converse_sync(prompt: str, messages: List[Dict[str, str]], model=None) -> Tuple[str, List[Dict[str, str]]]:
    config = resolve_config()
    if not config.is_ready:
        missing = ", ".join(config.missing_requirements)
        raise ValueError(f"{config.provider.label} is missing: {missing}.")

    if model is None:
        model = config.model
    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url)

    # Add the user's message to the list of messages
    if messages is None:
        messages = []

    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=_sanitize_messages_for_api(messages),
    ).choices[0].message.content

    # Add the assistant's message to the list of messages
    messages.append({"role": "assistant", "content": response})

    return response, messages


async def converse(messages: List[Dict[str, str]], max_tokens: int = 1600) -> AsyncGenerator[str, None]:
    """
    Given a conversation history, generate an iterative response of strings from a compatible LLM provider.

    :param messages: a conversation history with the following format:
    `[ { "role": "user", "content": "Hello, how are you?" },
       { "role": "assistant", "content": "I am doing well, how can I help you today?" } ]`
    :param max_tokens: maximum number of tokens to generate (default 1600)

    :return: a generator of delta string responses
    """
    config = resolve_config()
    if not config.is_ready:
        missing = ", ".join(config.missing_requirements)
        yield f"EXCEPTION {config.provider.label} is missing: {missing}."
        return

    model = config.model
    aclient = AsyncOpenAI(
        api_key=config.api_key,
        base_url=config.base_url
    )
    try:
        async for chunk in await aclient.chat.completions.create(model=model,
                                                                 messages=_sanitize_messages_for_api(messages),
                                                                 max_tokens=max_tokens,
                                                                 stream=True):
            content = chunk.choices[0].delta.content
            if content:
                yield content

    except OpenAIError as e:
        traceback.print_exc()
        yield f"oaiEXCEPTION {str(e)}"
    except Exception as e:
        yield f"EXCEPTION {str(e)}"
