# Compatible LLM Provider

This provider communicates with any Large Language Model (LLM) that exposes an OpenAI-compatible API.

## Supported Providers

The following providers can be used without changing the application code:

- OpenAI
- Google Gemini (OpenAI-compatible endpoint)
- Groq
- Together AI
- OpenRouter
- Any provider implementing the OpenAI Chat Completions API

## Configuration

The provider is configured through the project's `.env` file.

Example for OpenAI:

```env
LLM_PROVIDER=openai
LLM_API_KEY=<your-api-key>
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

Example for Google Gemini:

```env
LLM_PROVIDER=gemini
LLM_API_KEY=<your-api-key>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash
```

## Adding Another Provider

If the provider supports the OpenAI-compatible Chat Completions API, no code changes are required. Simply update the values in the `.env` file.

If the provider does **not** support the OpenAI-compatible API, create a new provider implementation under this directory and update `services/llm.py` to route requests accordingly.

## Architecture

```
Application
      │
      ▼
services/llm.py
      │
      ▼
services/providers/compatible_provider.py
      │
      ▼
Configured LLM Provider
```

The rest of the application should always communicate through `services.llm`. Provider-specific implementation details should remain isolated within the `providers` directory.