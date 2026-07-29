"""Helpers for company-then-person profile selection."""
from __future__ import annotations

from models.profile import Profile

UNASSIGNED_COMPANY = "(No company)"
SELECT_COMPANY = "--Select a company--"
SELECT_PROFILE = "--Select a profile--"


def company_label(profile: Profile) -> str:
    name = (profile.company_name or "").strip()
    return name if name else UNASSIGNED_COMPANY


def list_companies(profiles: list[Profile]) -> list[str]:
    companies = {company_label(profile) for profile in profiles}
    return sorted(
        companies,
        key=lambda name: (name == UNASSIGNED_COMPANY, name.lower()),
    )


def profiles_for_company(
    profiles: list[Profile],
    company: str,
) -> list[Profile]:
    matched = [
        profile
        for profile in profiles
        if company_label(profile) == company
    ]
    return sorted(
        matched,
        key=lambda profile: (
            profile.last_name.lower(),
            profile.first_name.lower(),
        ),
    )
