"""Catalog of saved prompts across AIDDI features.

Prototype only: reads from the current filesystem / in-code prompt sources.
This will move to the database once that design lands.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from services import prompt_templates, prompts, team_diagnostics

GROWTH_PLAN_SYSTEM_PROMPT = Path("data/GrowthPlan/growth_plan_system_prompt.md")

FEATURES = (
    "Growth Plan",
    "Team Diagnostics",
    "Quick Chat",
)


@dataclass(frozen=True)
class SavedPrompt:
    id: str
    feature: str
    name: str
    system_prompt: str
    output_format: str = ""
    source: str = ""


def _growth_plan_prompt() -> Optional[SavedPrompt]:
    if not GROWTH_PLAN_SYSTEM_PROMPT.exists():
        return None
    return SavedPrompt(
        id="growth_plan:default",
        feature="Growth Plan",
        name="default",
        system_prompt=GROWTH_PLAN_SYSTEM_PROMPT.read_text(encoding="utf-8"),
        source=str(GROWTH_PLAN_SYSTEM_PROMPT),
    )


def _team_diagnostics_prompts() -> List[SavedPrompt]:
    team_diagnostics.init_prompt_templates()

    results: List[SavedPrompt] = []
    for name in prompt_templates.list_templates():
        template = prompt_templates.load_template(name)
        results.append(
            SavedPrompt(
                id=f"team_diagnostics:{name}",
                feature="Team Diagnostics",
                name=name,
                system_prompt=template["system_prompt"],
                output_format=template.get("output_format", ""),
                source=f"data/TeamDiagnostics/Prompts/{name}",
            )
        )
    return results


def _quick_chat_prompt() -> SavedPrompt:
    return SavedPrompt(
        id="quick_chat:default",
        feature="Quick Chat",
        name="default",
        system_prompt=prompts.quick_chat_system_prompt().strip(),
        source="services/prompts.py",
    )


def list_saved_prompts(feature: Optional[str] = None) -> List[SavedPrompt]:
    """Return all known prompts, optionally filtered by feature label."""
    items: List[SavedPrompt] = []

    growth = _growth_plan_prompt()
    if growth:
        items.append(growth)

    items.extend(_team_diagnostics_prompts())
    items.append(_quick_chat_prompt())

    if feature and feature != "All":
        items = [item for item in items if item.feature == feature]

    return sorted(items, key=lambda item: (item.feature, item.name))


def get_saved_prompt(prompt_id: str) -> Optional[SavedPrompt]:
    for item in list_saved_prompts():
        if item.id == prompt_id:
            return item
    return None


def save_prompt_content(
    prompt_id: str,
    system_prompt: str,
    output_format: str = "",
) -> SavedPrompt:
    """Persist edits for supported filesystem-backed prompts."""
    if prompt_id.startswith("team_diagnostics:"):
        name = prompt_id.split(":", 1)[1]
        prompt_templates.save_template(name, system_prompt, output_format)
        updated = get_saved_prompt(prompt_id)
        if updated is None:
            raise FileNotFoundError(f"Prompt '{prompt_id}' not found after save.")
        return updated

    if prompt_id == "growth_plan:default":
        GROWTH_PLAN_SYSTEM_PROMPT.parent.mkdir(parents=True, exist_ok=True)
        GROWTH_PLAN_SYSTEM_PROMPT.write_text(system_prompt, encoding="utf-8")
        updated = get_saved_prompt(prompt_id)
        if updated is None:
            raise FileNotFoundError("Growth Plan prompt not found after save.")
        return updated

    raise ValueError(
        "This prompt is defined in code and cannot be edited here yet "
        f"({prompt_id})."
    )


def create_team_diagnostics_template(
    name: str,
    system_prompt: str,
    output_format: str,
) -> SavedPrompt:
    saved_name = prompt_templates.save_template(name, system_prompt, output_format)
    prompt_id = f"team_diagnostics:{saved_name}"
    created = get_saved_prompt(prompt_id)
    if created is None:
        raise FileNotFoundError(f"Created prompt '{prompt_id}' could not be loaded.")
    return created


def is_editable(prompt: SavedPrompt) -> bool:
    return prompt.feature in {"Growth Plan", "Team Diagnostics"}
