from dotenv import load_dotenv
from typing import List, Dict


from services.providers import compatible_provider

# Load .env file
load_dotenv()


def create_conversation_starter(user_prompt: str) -> List[Dict[str, str]]:
    """
    Given a user prompt, create a conversation history with the following format:
    :return: a conversation history
    """
    return [{"role": "user", "content": user_prompt}]


def converse(*args, **kwargs):
    return compatible_provider.converse(*args, **kwargs)


def converse_sync(*args, **kwargs):
    return compatible_provider.converse_sync(*args, **kwargs)
