"""Team Diagnostics service: teams, profile-linked members, prompts, and outputs.

Team membership is stored as profile IDs so personality and job-function
inputs stay consistent with the rest of the app. Filesystem storage is
temporary until the shared database lands.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from models.document_type import DocumentType
from models.profile import Profile
from repositories.profile_repository import ProfileRepository
from services import prompt_templates

TEAM_DIAGNOSTICS_DIR = Path("data/TeamDiagnostics")
INPUT_DIR = TEAM_DIAGNOSTICS_DIR / "Inputs"
OUTPUT_DIR = TEAM_DIAGNOSTICS_DIR / "Outputs"
SYSTEM_PROMPT_FILE = TEAM_DIAGNOSTICS_DIR / "team_diagnostics_system_prompt.md"
OUTPUT_FORMAT_FILE = TEAM_DIAGNOSTICS_DIR / "team_diagnostics_output_format.md"
TEAM_CONFIG_FILE = "team.json"

AUDIENCES = ("Facilitator", "Manager", "Peer")

OUTPUT_OPTIONS = (
    "Team Dynamics Blueprint",
    "At Your Best / Under Stress",
    "Coaching Cards",
    "Pair Discussion Guides",
)


def init_prompt_templates() -> None:
    """Seed the default saved prompt template from bundled markdown files."""
    prompt_templates.ensure_default_template(
        load_bundled_system_prompt(),
        load_bundled_output_format(),
    )


def normalize_team_name(team_name: str) -> str:
    """Normalize a display team name into a folder-safe identifier."""
    team_name = team_name.strip()
    team_name = re.sub(r"[\s,]+", "_", team_name)
    team_name = re.sub(r"[^A-Za-z0-9_]", "", team_name)
    team_name = re.sub(r"_+", "_", team_name).strip("_")
    return team_name


def team_folder(team_name: str) -> Path:
    return INPUT_DIR / normalize_team_name(team_name)


def team_config_path(team_name: str) -> Path:
    return team_folder(team_name) / TEAM_CONFIG_FILE


def _default_team_config(team_name: str, display_name: str = "") -> dict:
    folder_name = normalize_team_name(team_name)
    return {
        "name": folder_name,
        "display_name": display_name.strip() or folder_name.replace("_", " "),
        "company_info": "",
        "team_info": "",
        "member_profile_ids": [],
    }


def load_team_config(team_name: str) -> dict:
    path = team_config_path(team_name)
    if not path.exists():
        config = _default_team_config(team_name)
        save_team_config(team_name, config)
        return config

    data = json.loads(path.read_text(encoding="utf-8"))
    defaults = _default_team_config(team_name)
    defaults.update(data)
    if not isinstance(defaults.get("member_profile_ids"), list):
        defaults["member_profile_ids"] = []
    return defaults


def save_team_config(team_name: str, config: dict) -> Path:
    folder = team_folder(team_name)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / TEAM_CONFIG_FILE
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def create_team(
    team_name: str,
    company_info: str = "",
    team_info: str = "",
) -> Tuple[str, bool]:
    """Create a team. Returns (folder_name, existed)."""
    folder_name = normalize_team_name(team_name)
    if not folder_name:
        raise ValueError("Team name is required.")
    if not re.fullmatch(r"[A-Za-z0-9_]+", folder_name):
        raise ValueError("Team name may only contain letters, numbers, and spaces.")

    folder = INPUT_DIR / folder_name
    existed = folder.exists() and team_config_path(folder_name).exists()
    folder.mkdir(parents=True, exist_ok=True)

    if not existed:
        config = _default_team_config(folder_name, display_name=team_name)
        config["company_info"] = company_info.strip()
        config["team_info"] = team_info.strip()
        save_team_config(folder_name, config)

    return folder_name, existed


def update_team_context(
    team_name: str,
    company_info: str,
    team_info: str,
    display_name: str = "",
) -> dict:
    config = load_team_config(team_name)
    if display_name.strip():
        config["display_name"] = display_name.strip()
    config["company_info"] = company_info.strip()
    config["team_info"] = team_info.strip()
    save_team_config(team_name, config)
    return config


def list_teams() -> List[str]:
    """List available team folders under data/TeamDiagnostics/Inputs."""
    if not INPUT_DIR.exists():
        return []
    return sorted(p.name for p in INPUT_DIR.iterdir() if p.is_dir())


def list_member_profile_ids(team_name: str) -> List[str]:
    return list(load_team_config(team_name).get("member_profile_ids", []))


def add_member_profile(team_name: str, profile_id: str) -> dict:
    config = load_team_config(team_name)
    members = list(config.get("member_profile_ids", []))
    if profile_id in members:
        raise ValueError("That profile is already on this team.")
    members.append(profile_id)
    config["member_profile_ids"] = members
    save_team_config(team_name, config)
    return config


def remove_member_profile(team_name: str, profile_id: str) -> dict:
    config = load_team_config(team_name)
    members = [
        member_id
        for member_id in config.get("member_profile_ids", [])
        if member_id != profile_id
    ]
    config["member_profile_ids"] = members
    save_team_config(team_name, config)
    return config


def member_status(
    profile: Profile,
    repo: ProfileRepository,
) -> Dict[str, object]:
    has_personality = repo.document_exists(profile, DocumentType.PERSONALITY)
    has_job_functions = repo.document_exists(profile, DocumentType.JOB_FUNCTIONS)
    return {
        "profile_id": profile.id,
        "display_name": profile.display_name,
        "company_name": profile.company_name,
        "has_personality": has_personality,
        "has_job_functions": has_job_functions,
        "is_ready": has_personality and has_job_functions,
    }


def team_member_statuses(
    team_name: str,
    repo: ProfileRepository,
) -> List[Dict[str, object]]:
    statuses: List[Dict[str, object]] = []
    for profile_id in list_member_profile_ids(team_name):
        try:
            profile = repo.get_profile(profile_id)
        except FileNotFoundError:
            statuses.append(
                {
                    "profile_id": profile_id,
                    "display_name": f"Missing profile ({profile_id[:8]}…)",
                    "company_name": "",
                    "has_personality": False,
                    "has_job_functions": False,
                    "is_ready": False,
                    "missing_profile": True,
                }
            )
            continue
        statuses.append(member_status(profile, repo))
    return statuses


def validate_team(
    team_name: str,
    repo: ProfileRepository,
) -> Tuple[bool, List[Dict[str, object]], List[str]]:
    """Require at least two ready members (personality + job functions)."""
    statuses = team_member_statuses(team_name, repo)
    issues: List[str] = []

    if len(statuses) < 2:
        issues.append("Add at least two team members from Profiles.")

    missing_personality = [
        status["display_name"]
        for status in statuses
        if not status.get("has_personality")
    ]
    missing_jobs = [
        status["display_name"]
        for status in statuses
        if not status.get("has_job_functions")
    ]
    if missing_personality:
        issues.append(
            "Missing personality assessments for: "
            + ", ".join(missing_personality)
            + ". Update them on the Profiles / Growth Plan inputs."
        )
    if missing_jobs:
        issues.append(
            "Missing job functions for: "
            + ", ".join(missing_jobs)
            + ". Update them on the Profiles / Growth Plan inputs."
        )

    return len(issues) == 0, statuses, issues


def load_bundled_system_prompt() -> str:
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def load_bundled_output_format() -> str:
    return OUTPUT_FORMAT_FILE.read_text(encoding="utf-8")


def list_prompt_templates() -> List[str]:
    init_prompt_templates()
    return prompt_templates.list_templates()


def load_prompt_template(name: str) -> Dict[str, str]:
    init_prompt_templates()
    return prompt_templates.load_template(name)


def save_prompt_template(name: str, system_prompt: str, output_format: str) -> str:
    return prompt_templates.save_template(name, system_prompt, output_format)


def build_system_message(template_name: str) -> str:
    init_prompt_templates()
    return prompt_templates.build_system_message(template_name)


def build_user_prompt(
    team_name: str,
    audience: str,
    outputs: List[str],
    repo: ProfileRepository,
) -> str:
    """Combine team context, profile inputs, and run configuration."""
    config = load_team_config(team_name)
    display_name = config.get("display_name") or team_name
    company_info = (config.get("company_info") or "").strip()
    team_info = (config.get("team_info") or "").strip()

    member_blocks: List[str] = []
    member_names: List[str] = []

    for profile_id in list_member_profile_ids(team_name):
        profile = repo.get_profile(profile_id)
        member_names.append(profile.display_name)
        personality = repo.load_document(profile, DocumentType.PERSONALITY)
        job_functions = repo.load_document(profile, DocumentType.JOB_FUNCTIONS)
        member_blocks.append(
            f"## {profile.display_name}\n\n"
            f"### Personality Assessment\n\n```markdown\n{personality}\n```\n\n"
            f"### Job Functions\n\n```markdown\n{job_functions}\n```"
        )

    output_list = "\n".join(f"- {output}" for output in outputs)
    context_sections = []
    if company_info:
        context_sections.append(f"## Company / organization\n\n{company_info}")
    if team_info:
        context_sections.append(f"## Team context\n\n{team_info}")
    context_block = "\n\n".join(context_sections) if context_sections else "_No additional company or team context provided._"

    return f"""
Generate a Team Diagnostics packet for team **{display_name}**.

# Run Configuration

- **Audience:** {audience}
- **Team members:** {", ".join(member_names)}
- **Requested outputs:**

{output_list}

Only generate the outputs listed above. Use the exact headings from the output format specification.

# Company and team context

{context_block}

# Member inputs

{chr(10).join(member_blocks)}
""".strip()


def output_path(team_name: str, template_name: str = "") -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{template_name}" if template_name else ""
    return OUTPUT_DIR / f"TeamDiagnostics_{normalize_team_name(team_name)}{suffix}.md"


def save_team_diagnostics(team_name: str, content: str, template_name: str = "") -> Path:
    path = output_path(team_name, template_name=template_name)
    path.write_text(content, encoding="utf-8")
    return path


def list_saved_outputs(team_name: str) -> List[Path]:
    if not OUTPUT_DIR.exists():
        return []
    prefix = f"TeamDiagnostics_{normalize_team_name(team_name)}"
    matches = [
        path
        for path in OUTPUT_DIR.glob(f"{prefix}*.md")
        if path.is_file()
    ]
    return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)


def load_saved_output(team_name: str, template_name: str = "") -> Optional[str]:
    if template_name:
        exact = output_path(team_name, template_name=template_name)
        if exact.exists():
            return exact.read_text(encoding="utf-8")

    saved = list_saved_outputs(team_name)
    if not saved:
        return None
    return saved[0].read_text(encoding="utf-8")
