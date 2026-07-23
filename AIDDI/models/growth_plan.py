from dataclasses import dataclass
from datetime import datetime

@dataclass
class GrowthPlan:
    id: str
    profile_id: str
    title: str
    content: str
    created: datetime
    modified: datetime
