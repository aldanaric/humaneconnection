from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator, Tuple

class LLMService(ABC):
    """
    Abstract interface supporting both synchronous and asynchronous conversation 
    across different Large Language Model (LLM) providers.
    """
    
    @abstractmethod
    def converse_sync(self, prompt: str, messages: List[Dict[str, str]], model: str = None) -> Tuple[str, List[Dict[str, str]]]:
        """
        Given a user prompt and a conversation history, append the prompt, 
        execute a synchronous/blocking call to the LLM API, append the assistant's 
        response, and return both the text and the updated history.

        :param prompt: The new user message string to send.
        :param messages: A conversation history list of message dictionaries.
        :param model: Optional override for the target deployment model string.
        :return: A tuple containing (response_string, updated_messages_list).
        """
        pass

    @abstractmethod
    async def converse(self, messages: List[Dict[str, str]], max_tokens: int = 1600) -> AsyncGenerator[str, None]:
        """
        Given a conversation history, generate an iterative response of strings from the LLM API.

        :param messages: A conversation history with the following format:
            `[ { "role": "user", "content": "Hello, how are you?" },
               { "role": "assistant", "content": "I am doing well, how can I help you today?" } ]`
        :param max_tokens: Maximum number of tokens to generate (default 1600).
        :return: An async generator yielding delta string responses (token chunks).
        """
        pass

    def create_conversation_starter(self, user_prompt: str) -> List[Dict[str, str]]:
        """
        Given a user prompt, create a conversation history with the following format:
        `[ { "role": "user", "content": user_prompt } ]`

        :param user_prompt: A user prompt string.
        :return: A conversation history list containing the initial user message.
        """
        return [{"role": "user", "content": user_prompt}]