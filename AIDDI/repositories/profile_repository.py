import json
import uuid
from pathlib import Path
from pypdf import PdfReader
from enum import Enum

from models.profile import Profile

class DocumentType(Enum):
    PERSONALITY = "personality"
    JOB_FUNCTIONS = "job_functions"
    OBSERVATIONS = "observations"
    GROWTH_PLAN = "growth_plan"

class ProfileRepository:
    """Repository for creating, loading, and saving Growth Plan profiles"""

    PROFILE_FILE = "profile.json"

    DOCUMENTS = {
        "personality": "personality.md",
        "job_functions": "job_functions.md",
        "observations": "observations.md",
        "growth_plan": "growth_plan.md"
    }

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create_profile(
        self,
    first_name: str,
    last_name: str
    ) -> Profile:
        """Create a new profile"""

        profile_id = str(uuid.uuid4())
        folder = self.root / profile_id
        folder.mkdir(parents=True)

        profile = Profile(
            id = profile_id,
            first_name = first_name,
            last_name = last_name,
            root = folder
        )

        self._save_profile_metadata(profile)

        return profile

    def list_profiles(self) -> list[Profile]:
        """Return every profile"""

        profiles = []

        if not self.root.exists():
            return profiles

        for folder in self.root.iterdir():
            if not folder.is_dir():
                continue

            metadata = folder / self.PROFILE_FILE

            if not metadata.exists():
                continue

            data = json.loads(metadata.read_text(encoding="utf-8"))

            profiles.append(
                Profile(
                    id=data["id"],
                    first_name=data["first_name"],
                    last_name = data["last_name"],
                    root = folder,
                )
            )

        return sorted(profiles, key=lambda p: (p.last_name, p.first_name))

    def get_profile(self, profile_id):


    def save_personality(self, profile_id, text):


    def load_personality(self, profile_id):

    def _save_profile_metadata(self, profile):
        pass
