import re
from pathlib import Path
from typing import Dict, List, Tuple

from services import prompt_templates

TEAM_DIAGNOSTICS_DIR = Path("data/TeamDiagnostics")
INPUT_DIR = TEAM_DIAGNOSTICS_DIR / "Inputs"
OUTPUT_DIR = TEAM_DIAGNOSTICS_DIR / "Outputs"
SYSTEM_PROMPT_FILE = TEAM_DIAGNOSTICS_DIR / "team_diagnostics_system_prompt.md"
OUTPUT_FORMAT_FILE = TEAM_DIAGNOSTICS_DIR / "team_diagnostics_output_format.md"


def init_prompt_templates() -> None:
    """Seed the default saved prompt template from bundled markdown files."""
    prompt_templates.ensure_default_template(
        load_bundled_system_prompt(),
        load_bundled_output_format(),
    )

AUDIENCES = ("Facilitator", "Manager", "Peer")

OUTPUT_OPTIONS = (
    "Team Dynamics Blueprint",
    "At Your Best / Under Stress",
    "Coaching Cards",
    "Pair Discussion Guides",
)


def normalize_team_name(team_name: str) -> str:
    """Normalize a display team name into a folder-safe identifier."""
    team_name = team_name.strip()
    team_name = re.sub(r"[\s,]+", "_", team_name)
    team_name = re.sub(r"[^A-Za-z0-9_]", "", team_name)
    team_name = re.sub(r"_+", "_", team_name).strip("_")
    return team_name


def create_team_folder(team_name: str) -> Tuple[Path, bool]:
    """Create a team folder under INPUT_DIR. Returns (folder, existed)."""
    folder_name = normalize_team_name(team_name)
    if not folder_name:
        raise ValueError("Team name is required.")
    if not re.fullmatch(r"[A-Za-z0-9_]+", folder_name):
        raise ValueError("Team name may only contain letters, numbers, and spaces.")

    folder = INPUT_DIR / folder_name
    existed = folder.exists()
    folder.mkdir(parents=True, exist_ok=True)
    return folder, existed


def split_last_first(folder_name: str) -> Tuple[str, str]:
    """Return (last, first) from a Last_First folder name."""
    parts = folder_name.split("_", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Member folders must be named Last_First.")
    return parts[0], parts[1]


def create_member_folder(team_name: str, member_name: str) -> Tuple[Path, bool]:
    """Create a Last_First member folder under a team. Returns (folder, existed)."""
    team_folder = INPUT_DIR / normalize_team_name(team_name)
    if not team_folder.exists():
        raise ValueError(f"Team '{team_name}' does not exist.")

    member_name = member_name.strip().replace(",", "_")
    member_name = re.sub(r"\s+", "", member_name)

    if not re.fullmatch(r"[A-Za-z]+_[A-Za-z]+", member_name):
        raise ValueError("Member name must be in the format Last_First.")

    folder = team_folder / member_name
    existed = folder.exists()
    folder.mkdir(parents=True, exist_ok=True)
    return folder, existed


def save_uploaded_file(uploaded_file, destination: Path) -> None:
    if uploaded_file is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(uploaded_file.getbuffer())


def list_teams() -> List[str]:
    """List available team folders under data/TeamDiagnostics/Inputs."""
    if not INPUT_DIR.exists():
        return []

    return sorted(p.name for p in INPUT_DIR.iterdir() if p.is_dir())


def list_members(team_name: str) -> List[str]:
    """List Last_First member folders for a team."""
    team_folder = INPUT_DIR / normalize_team_name(team_name)
    if not team_folder.exists():
        return []

    return sorted(
        p.name for p in team_folder.iterdir()
        if p.is_dir() and "_" in p.name
    )


def personality_path(team_name: str, member_name: str) -> Path:
    """Canonical personality assessment path for a team member."""
    last, first = split_last_first(member_name)
    return (
        INPUT_DIR
        / normalize_team_name(team_name)
        / member_name
        / f"Personality_Assessment_{first}_{last}.md"
    )


def member_status(team_name: str, member_name: str) -> Dict[str, object]:
    """Return status metadata for one team member."""
    path = personality_path(team_name, member_name)
    last, first = split_last_first(member_name)
    return {
        "member_name": member_name,
        "display_name": f"{first} {last}",
        "personality_path": path,
        "has_personality": path.exists(),
    }


def team_member_statuses(team_name: str) -> List[Dict[str, object]]:
    """Return status metadata for every member on a team."""
    return [member_status(team_name, member) for member in list_members(team_name)]


def validate_team(team_name: str) -> Tuple[bool, List[Dict[str, object]], List[str]]:
    """
    Check whether the team has at least two members with personality assessments.

    Returns (is_valid, member_statuses, issues).
    """
    statuses = team_member_statuses(team_name)
    issues: List[str] = []

    if len(statuses) < 2:
        issues.append("Add at least two team members.")

    missing = [
        status["display_name"]
        for status in statuses
        if not status["has_personality"]
    ]
    if missing:
        issues.append(f"Missing personality assessments for: {', '.join(missing)}")

    return len(issues) == 0, statuses, issues


def read_personality_assessments(team_name: str) -> Dict[str, str]:
    """Read all personality assessments for a team. Keys are display names."""
    assessments: Dict[str, str] = {}
    for status in team_member_statuses(team_name):
        path = status["personality_path"]
        if path.exists():
            assessments[str(status["display_name"])] = path.read_text(encoding="utf-8")
    return assessments


def load_bundled_system_prompt() -> str:
    """Load the bundled Team Diagnostics system prompt."""
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def load_bundled_output_format() -> str:
    """Load the bundled Team Diagnostics output format specification."""
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
) -> str:
    """Combine team inputs and run configuration into the user prompt."""
    assessments = read_personality_assessments(team_name)
    members = ", ".join(assessments.keys())

    assessment_blocks = "\n\n".join(
        f"## {name}\n\n```markdown\n{content}\n```"
        for name, content in assessments.items()
    )

    output_list = "\n".join(f"- {output}" for output in outputs)

    return f"""
Generate a Team Diagnostics packet for team **{team_name}**.

# Run Configuration

- **Audience:** {audience}
- **Team members:** {members}
- **Requested outputs:**

{output_list}

Only generate the outputs listed above. Use the exact headings from the output format specification.

# Personality Assessments

{assessment_blocks}
""".strip()


def output_path(team_name: str, template_name: str = "") -> Path:
    """Return output path for a team, optionally scoped to a prompt template."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{template_name}" if template_name else ""
    return OUTPUT_DIR / f"TeamDiagnostics_{normalize_team_name(team_name)}{suffix}.md"


def save_team_diagnostics(team_name: str, content: str, template_name: str = "") -> Path:
    """Save model output as markdown and return the path."""
    path = output_path(team_name, template_name=template_name)
    path.write_text(content, encoding="utf-8")
    return path


def list_saved_outputs(team_name: str) -> List[Path]:
    """List saved output files for a team, newest first."""
    if not OUTPUT_DIR.exists():
        return []

    prefix = f"TeamDiagnostics_{normalize_team_name(team_name)}"
    matches = [
        path
        for path in OUTPUT_DIR.glob(f"{prefix}*.md")
        if path.is_file()
    ]
    return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)


def load_saved_output(team_name: str, template_name: str = "") -> str | None:
    """
    Return saved output for a team.

    Prefers an exact template match when template_name is provided.
    Otherwise returns the most recently modified matching file.
    """
    if template_name:
        exact = output_path(team_name, template_name=template_name)
        if exact.exists():
            return exact.read_text(encoding="utf-8")

    saved = list_saved_outputs(team_name)
    if not saved:
        return None
    return saved[0].read_text(encoding="utf-8")
