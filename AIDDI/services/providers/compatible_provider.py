import traceback

from typing import List, Dict, Tuple, AsyncGenerator

from openai import AsyncOpenAI, OpenAI, OpenAIError

from services.llm_config import resolve_config




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
        messages=messages,
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
                                                                 messages=messages,
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
