from dataclasses import dataclass
from datetime import datetime


@dataclass
class Team:
    id: str
    account_id: str
    name: str
    display_name: str
    company_info: str
    team_info: str
    created_at: datetime
    updated_at: datetime
    member_profile_ids: list[str] | None = None
