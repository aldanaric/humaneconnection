import re
from pathlib import Path
from typing import Dict, List

PROMPTS_DIR = Path("data/TeamDiagnostics/Prompts")
SYSTEM_FILENAME = "system_prompt.md"
OUTPUT_FORMAT_FILENAME = "output_format.md"
DEFAULT_TEMPLATE = "default"



# For now this will save files to the data/TeamDiagnostics/Prompts directory. Likley will need to change and use a database for this and other such data. 

def _normalize_template_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[\s,]+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def _template_dir(name: str) -> Path:
    return PROMPTS_DIR / _normalize_template_name(name)


def ensure_default_template(
    system_prompt: str,
    output_format: str,
) -> None:
    """Create the default template from bundled prompt files if none exist."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    default_dir = _template_dir(DEFAULT_TEMPLATE)
    if default_dir.exists():
        return

    default_dir.mkdir(parents=True, exist_ok=True)
    (default_dir / SYSTEM_FILENAME).write_text(system_prompt, encoding="utf-8")
    (default_dir / OUTPUT_FORMAT_FILENAME).write_text(output_format, encoding="utf-8")


def list_templates() -> List[str]:
    if not PROMPTS_DIR.exists():
        return []
    return sorted(
        p.name
        for p in PROMPTS_DIR.iterdir()
        if p.is_dir() and (p / SYSTEM_FILENAME).exists()
    )


def load_template(name: str) -> Dict[str, str]:
    folder = _template_dir(name)
    system_path = folder / SYSTEM_FILENAME
    output_path = folder / OUTPUT_FORMAT_FILENAME

    if not system_path.exists():
        raise FileNotFoundError(f"Prompt template '{name}' not found.")

    return {
        "name": folder.name,
        "system_prompt": system_path.read_text(encoding="utf-8"),
        "output_format": output_path.read_text(encoding="utf-8")
        if output_path.exists()
        else "",
    }


def save_template(name: str, system_prompt: str, output_format: str) -> str:
    folder_name = _normalize_template_name(name)
    if not folder_name:
        raise ValueError("Template name is required.")

    folder = PROMPTS_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / SYSTEM_FILENAME).write_text(system_prompt, encoding="utf-8")
    (folder / OUTPUT_FORMAT_FILENAME).write_text(output_format, encoding="utf-8")
    return folder_name


def build_system_message(template_name: str) -> str:
    template = load_template(template_name)
    parts = [template["system_prompt"].strip()]
    if template["output_format"].strip():
        parts.append("# Output Format\n\n" + template["output_format"].strip())
    return "\n\n".join(parts)
