from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from models.account import Account
from models.document_type import DocumentType
from models.profile import Profile
from models.team import Team
from models.team_diagnostic_report import TeamDiagnosticReport
from repositories.profile_repository import ProfileRepository
from repositories.team_diagnostics_repository import TeamDiagnosticsRepository
from services import prompt_templates

TEAM_DIAGNOSTICS_DIR = Path("data/TeamDiagnostics")
SYSTEM_PROMPT_FILE = TEAM_DIAGNOSTICS_DIR / "team_diagnostics_system_prompt.md"
OUTPUT_FORMAT_FILE = TEAM_DIAGNOSTICS_DIR / "team_diagnostics_output_format.md"

AUDIENCES = ("Facilitator", "Manager", "Peer")

OUTPUT_OPTIONS = (
    "Team Dynamics Blueprint",
    "At Your Best / Under Stress",
    "Coaching Cards",
    "Pair Discussion Guides",
)

_repo = TeamDiagnosticsRepository()


def init_prompt_templates() -> None:
    """Seed the default saved prompt template from bundled markdown files."""
    prompt_templates.ensure_default_template(
        load_bundled_system_prompt(),
        load_bundled_output_format(),
    )


def normalize_team_name(team_name: str) -> str:
    """Normalize a display team name into a stable identifier."""
    team_name = team_name.strip()
    team_name = re.sub(r"[\s,]+", "_", team_name)
    team_name = re.sub(r"[^A-Za-z0-9_]", "", team_name)
    team_name = re.sub(r"_+", "_", team_name).strip("_")
    return team_name


def create_team(
    account: Account,
    team_name: str,
    company_info: str = "",
    team_info: str = "",
) -> Tuple[str, bool]:
    """Create a team. Returns (name, existed)."""
    folder_name = normalize_team_name(team_name)
    if not folder_name:
        raise ValueError("Team name is required.")
    if not re.fullmatch(r"[A-Za-z0-9_]+", folder_name):
        raise ValueError("Team name may only contain letters, numbers, and spaces.")

    existing = _repo.get_team_by_name(account.id, folder_name)
    if existing is not None:
        return folder_name, True

    _repo.create_team(
        account.id,
        name=folder_name,
        display_name=team_name.strip() or folder_name.replace("_", " "),
        company_info=company_info.strip(),
        team_info=team_info.strip(),
    )
    return folder_name, False


def load_team(account: Account, team_name: str) -> Team:
    team = _repo.get_team_by_name(account.id, team_name)
    if team is None:
        raise FileNotFoundError(team_name)
    return team


def load_team_config(account: Account, team_name: str) -> dict:
    """Return a config-shaped dict for UI compatibility."""
    team = load_team(account, team_name)
    return {
        "id": team.id,
        "name": team.name,
        "display_name": team.display_name,
        "company_info": team.company_info,
        "team_info": team.team_info,
        "member_profile_ids": list(team.member_profile_ids or []),
    }


def update_team_context(
    account: Account,
    team_name: str,
    company_info: str,
    team_info: str,
    display_name: str = "",
) -> dict:
    team = _repo.update_team_context(
        account.id,
        team_name,
        display_name=display_name,
        company_info=company_info.strip(),
        team_info=team_info.strip(),
    )
    return {
        "id": team.id,
        "name": team.name,
        "display_name": team.display_name,
        "company_info": team.company_info,
        "team_info": team.team_info,
        "member_profile_ids": list(team.member_profile_ids or []),
    }


def list_teams(account: Account) -> List[str]:
    """List team name identifiers for the logged-in account."""
    return [team.name for team in _repo.list_teams(account.id)]


def list_team_records(account: Account) -> List[Team]:
    return _repo.list_teams(account.id)


def list_member_profile_ids(account: Account, team_name: str) -> List[str]:
    return _repo.list_member_profile_ids(account.id, team_name)


def add_member_profile(
    account: Account,
    team_name: str,
    profile: Profile,
) -> dict:
    team = _repo.add_member(account.id, team_name, profile.id)
    return {
        "id": team.id,
        "name": team.name,
        "display_name": team.display_name,
        "company_info": team.company_info,
        "team_info": team.team_info,
        "member_profile_ids": list(team.member_profile_ids or []),
    }


def remove_member_profile(
    account: Account,
    team_name: str,
    profile_id: str,
) -> dict:
    team = _repo.remove_member(account.id, team_name, profile_id)
    return {
        "id": team.id,
        "name": team.name,
        "display_name": team.display_name,
        "company_info": team.company_info,
        "team_info": team.team_info,
        "member_profile_ids": list(team.member_profile_ids or []),
    }


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
    account: Account,
    team_name: str,
    repo: ProfileRepository,
) -> List[Dict[str, object]]:
    statuses: List[Dict[str, object]] = []
    for profile_id in list_member_profile_ids(account, team_name):
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
    account: Account,
    team_name: str,
    repo: ProfileRepository,
) -> Tuple[bool, List[Dict[str, object]], List[str]]:
    """Require at least two ready members (personality + job functions)."""
    statuses = team_member_statuses(account, team_name, repo)
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
    account: Account,
    team_name: str,
    audience: str,
    outputs: List[str],
    repo: ProfileRepository,
) -> str:
    """Combine team context, profile inputs, and run configuration."""
    config = load_team_config(account, team_name)
    display_name = config.get("display_name") or team_name
    company_info = (config.get("company_info") or "").strip()
    team_info = (config.get("team_info") or "").strip()

    member_blocks: List[str] = []
    member_names: List[str] = []

    for profile_id in list_member_profile_ids(account, team_name):
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
    context_block = (
        "\n\n".join(context_sections)
        if context_sections
        else "_No additional company or team context provided._"
    )

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


def save_team_diagnostics(
    account: Account,
    team_name: str,
    content: str,
    template_name: str = "",
    *,
    title: str | None = None,
    audience: str = "Facilitator",
    requested_outputs: List[str] | None = None,
    used_humane_connection: bool = False,
) -> TeamDiagnosticReport:
    """Create a new saved report (does not overwrite history)."""
    prompt_template_name = template_name or "default"
    resolved_title = (
        title.strip()
        if title and title.strip()
        else f"TeamDiagnostics_{normalize_team_name(team_name)}_{prompt_template_name}"
    )
    return _repo.create_report_always(
        account.id,
        team_name,
        content=content,
        prompt_template_name=prompt_template_name,
        title=resolved_title,
        audience=audience,
        requested_outputs=requested_outputs,
        used_humane_connection=used_humane_connection,
    )


def update_team_diagnostics(
    account: Account,
    report_id: str,
    *,
    content: str | None = None,
    title: str | None = None,
) -> TeamDiagnosticReport:
    return _repo.update_report(
        account.id,
        report_id,
        content=content,
        title=title,
    )


def get_saved_report(
    account: Account,
    report_id: str,
) -> Optional[TeamDiagnosticReport]:
    return _repo.get_report(account.id, report_id)


def delete_team_diagnostics(
    account: Account,
    report_id: str,
) -> None:
    _repo.delete_report(account.id, report_id)


def list_saved_outputs(
    account: Account,
    team_name: str,
) -> List[TeamDiagnosticReport]:
    return _repo.list_reports(account.id, team_name)


def load_saved_output(
    account: Account,
    team_name: str,
    template_name: str = "",
) -> Optional[str]:
    report = _repo.get_latest_report(
        account.id,
        team_name,
        prompt_template_name=template_name or None,
    )
    if report is None:
        return None
    return report.content


def load_latest_report(
    account: Account,
    team_name: str,
    template_name: str = "",
) -> Optional[TeamDiagnosticReport]:
    return _repo.get_latest_report(
        account.id,
        team_name,
        prompt_template_name=template_name or None,
    )