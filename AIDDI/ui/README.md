# UI Directory

This directory contains all Streamlit-related code for the AIDDI application, organized into a clear structure that separates different UI concerns.

## Directory Structure

- **components/**: Reusable UI components that can be used across multiple pages
  - `sidebar.py`: Sidebar component used on all pages

- **interactions/**: Handlers for UI interactions that connect the UI to services
  - `chat_handler.py`: Handles chat interactions with the LLM service
  - `book_handler.py`: Handles interactions with the RAG service for book queries

- **layouts/**: Page layout helpers for consistent UI structure
  - (To be populated as needed)

## Usage

Import components and interaction handlers as needed in your Streamlit pages:

```python
# Import a UI component
from ui.components import sidebar

# Import an interaction handler
from ui.interactions import chat_handler

# Use the component
sidebar.show()

# Use the interaction handler
messages = await chat_handler.chat(messages, prompt)
```

## Design Principles

1. **Separation of Concerns**: UI code is separated from business logic (services)
2. **Reusability**: Components are designed to be reused across multiple pages
3. **Consistency**: Common UI patterns are encapsulated in reusable components
4. **Maintainability**: Clear organization makes it easier to find and modify code
