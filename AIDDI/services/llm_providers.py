import os
import time
import asyncio
import traceback
from typing import List, Dict, AsyncGenerator, Tuple

from openai import AsyncOpenAI, OpenAIError, OpenAI
from google import genai

from .llm_base import LLMService

class GeminiProvider(LLMService):
    """
    Concrete implementation of LLMService using the official Google Gen AI SDK.
    Includes built-in exponential backoff for handling rate limits (429 errors).
    """
    def __init__(self):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # Default model deployment; can be modified as needed
        self.model_id = "gemini-2.5-flash"
        
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict]:
        """
        Translates OpenAI's standardized message format into Gemini's expected API structure.
        Maps the role 'assistant' to 'model' and structures content into parts.
        """
        gemini_contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        return gemini_contents

    def converse_sync(self, prompt: str, messages: List[Dict[str, str]], model: str = None) -> Tuple[str, List[Dict[str, str]]]:
        """
        Executes a blocking/synchronous call to the Gemini API with automatic 429 retry backoff.
        """
        if messages is None:
            messages = []
            
        messages.append({"role": "user", "content": prompt})
        gemini_contents = self._format_messages(messages)
        
        max_retries = 3
        backoff_factor = 5
        response_text = ""
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=model or self.model_id,
                    contents=gemini_contents
                )
                response_text = response.text
                break
            except Exception as e:
                # Synchronous rate-limit handling
                if "429" in str(e) or "Too Many Requests" in str(e):
                    if attempt == max_retries:
                        response_text = f"EXCEPTION Gemini API rate limit exceeded: {e}"
                        break
                    time.sleep(backoff_factor ** (attempt + 1))
                else:
                    response_text = f"EXCEPTION {str(e)}"
                    break

        messages.append({"role": "assistant", "content": response_text})
        return response_text, messages

    async def converse(self, messages: List[Dict[str, str]], max_tokens: int = 1600) -> AsyncGenerator[str, None]:
        """
        Executes an asynchronous, non-blocking streaming call via Gemini's aio client.
        Includes non-blocking token chunk generation and non-blocking backoff via asyncio.sleep.
        """
        gemini_contents = self._format_messages(messages)
        
        max_retries = 3
        backoff_factor = 5
        
        for attempt in range(max_retries + 1):
            try:
                # Streaming responses asynchronously requires using the asynchronous client object client.aio
                response_stream = await self.client.aio.models.generate_content_stream(
                    model=self.model_id,
                    contents=gemini_contents,
                )
                
                async for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return  # Exit successfully once the stream is completely yielded
                
            except Exception as e:
                # Asynchronous rate-limit handling
                if "429" in str(e) or "Too Many Requests" in str(e):
                    if attempt == max_retries:
                        yield f"EXCEPTION Gemini API rate limit exceeded: {e}"
                        return
                    # Use asyncio.sleep instead of time.sleep to protect the event loop thread
                    await asyncio.sleep(backoff_factor ** (attempt + 1))
                else:
                    traceback.print_exc()
                    yield f"EXCEPTION {str(e)}"
                    return


class LocalOpenAIProvider(LLMService):
    """
    Concrete implementation of LLMService using OpenAI-compatible structure.
    Used for local VT installations or standard OpenAI client endpoints.
    """
    def __init__(self):
        self.openai_model = os.getenv('OPENAI_API_MODEL')
        self.client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_API_BASE_URL')
        )
        self.aclient = AsyncOpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_API_BASE_URL')
        )

    def converse_sync(self, prompt: str, messages: List[Dict[str, str]], model: str = None) -> Tuple[str, List[Dict[str, str]]]:
        """
        Executes a blocking/synchronous chat completion request.
        """
        if model is None:
            model = self.openai_model
        
        if messages is None:
            messages = []

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
        ).choices[0].message.content

        messages.append({"role": "assistant", "content": response})
        return response, messages

    async def converse(self, messages: List[Dict[str, str]], max_tokens: int = 1600) -> AsyncGenerator[str, None]:
        """
        Executes an asynchronous chat completion request streaming token chunks in real-time.
        Safely evaluates chunk boundaries to prevent trailing index exceptions from usage statistics blocks.
        """
        try:
            # Awaiting the asynchronous creation of the stream
            stream = await self.aclient.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                max_tokens=max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                # Validate choices array availability to bypass downstream metadata trailing exceptions
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content

        except OpenAIError as e:
            traceback.print_exc()
            yield f"oaiEXCEPTION {str(e)}"
        except Exception as e:
            yield f"EXCEPTION {str(e)}"