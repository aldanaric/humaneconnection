from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TeamDiagnosticReport:
    id: str
    team_id: str
    account_id: str
    title: str
    content: str
    prompt_template_name: str
    audience: str
    requested_outputs: list[str] = field(default_factory=list)
    used_humane_connection: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
