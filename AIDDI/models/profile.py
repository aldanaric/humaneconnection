from dataclasses import dataclass
from pathlib import Path

@dataclass
class Profile:
    id: str
    first_name: str
    last_name: str
    root: Path

    @property
    def display_name(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def folder_name(self):
        return f"{self.last_name}_{self.first_name}"

    @property
    def personality_path(self) -> Path:
        return self.root / "personality.md"

    @property
    def job_functions_path(self) -> Path:
        return self.root / "job_functions.md"

    @property
    def observations_path(self) -> Path:
        return self.root / "observations.md"
