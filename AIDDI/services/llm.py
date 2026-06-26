import os
import traceback
from typing import List, Dict, AsyncGenerator, Tuple

import openai
from openai import AsyncOpenAI

from dotenv import load_dotenv
from openai import OpenAIError, OpenAI

# Load .env file
load_dotenv()


openai_model = os.getenv('OPENAI_API_MODEL')

def converse_sync(prompt: str, messages: List[Dict[str, str]], model=None) -> Tuple[str, List[Dict[str, str]]]:
    if model is None:
        model = openai_model
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_API_BASE_URL'))

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
    Given a conversation history, generate an iterative response of strings from the OpenAI API.

    :param messages: a conversation history with the following format:
    `[ { "role": "user", "content": "Hello, how are you?" },
       { "role": "assistant", "content": "I am doing well, how can I help you today?" } ]`
    :param max_tokens: maximum number of tokens to generate (default 1600)

    :return: a generator of delta string responses
    """
    aclient = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'),
                          base_url=os.getenv('OPENAI_API_BASE_URL'))
    try:
        async for chunk in await aclient.chat.completions.create(model=openai_model,
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


def create_conversation_starter(user_prompt: str) -> List[Dict[str, str]]:
    """
    Given a user prompt, create a conversation history with the following format:
    `[ { "role": "user", "content": user_prompt } ]`

    :param user_prompt: a user prompt string
    :return: a conversation history
    """
    return [{"role": "user", "content": user_prompt}]
