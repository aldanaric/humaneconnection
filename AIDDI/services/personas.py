from __future__ import annotations

from pathlib import Path
from typing import Dict, List


# Root directory for persona prompt files inside AIDDI project.  This is a relative path from the project root.
PERSONA_DIR = Path("data/personas")


# Start with the 3 required roles for the assignment.
# More roles can be added later without changing the public API.
ROLE_TO_FILE: Dict[str, str] = {
    "Architect": "Architecture and System Design Expert.md",
    "Developer": "Development Expert.md",
    "QA Lead": "Quinn2.md",
}


class PersonaError(Exception):
    """Raised when persona loading fails."""


def list_roles() -> List[str]:
    """Return available persona roles in UI-friendly order."""
    return list(ROLE_TO_FILE.keys())


def get_persona_path(role: str) -> Path:
    """
    Resolve the persona file path for a given role.

    Args:
        role: UI-facing role name

    Returns:
        Path to the persona file

    Raises:
        PersonaError: if the role is unknown
    """
    if role not in ROLE_TO_FILE:
        valid = ", ".join(list_roles())
        raise PersonaError(f"Unknown role '{role}'. Valid roles: {valid}")

    return PERSONA_DIR / ROLE_TO_FILE[role]


def load_persona(role: str) -> str:
    """
    Load persona prompt text for a given role.

    Args:
        role: UI-facing role name

    Returns:
        Persona text

    Raises:
        PersonaError: if the file is missing, unreadable, or empty
    """
    path = get_persona_path(role)

    if not path.exists():
        raise PersonaError(
            f"Persona file for role '{role}' was not found: {path}"
        )

    try:
        content = path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        raise PersonaError(
            f"Failed to read persona file for role '{role}': {path}"
        ) from exc

    if not content:
        raise PersonaError(f"Persona file is empty for role '{role}': {path}")

    return content


def build_system_message(role: str) -> Dict[str, str]:
    """
    Build the initial system message for a new conversation.

    Args:
        role: UI-facing role name

    Returns:
        OpenAI-style system message dict
    """
    persona_text = load_persona(role)
    return {"role": "system", "content": persona_text}