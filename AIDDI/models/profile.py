from dataclasses import dataclass
from pathlib import Path

@dataclass
class Profile:
    id: str
    first_name: str
    last_name: str
    company_name: str

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}"

