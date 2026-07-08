import json
import uuid
from pathlib import Path
from pypdf import PdfReader
from pathlib import Path
from datetime import datetime

from models.profile import Profile
from models.document_type import DocumentType
from models.growth_plan import GrowthPlan


class ProfileRepository:
    """Repository for creating, loading, and saving Growth Plan profiles"""

    PROFILE_FILE = "profile.json"

    def __init__(self):
        self.root = Path("data/GrowthPlan/Profiles")
        self.root.mkdir(parents=True, exist_ok=True)

    def create_profile(
        self,
        first_name: str,
        last_name: str,
        company_name: str
    ) -> Profile:
        """Create a new profile"""

        profile_id = str(uuid.uuid4())
        folder = self.root / profile_id
        folder.mkdir(parents=True)

        profile = Profile(
            id=profile_id,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            root=folder
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
                    last_name=data["last_name"],
                    company_name=data["company_name"],
                    root=folder,
                )
            )

        return sorted(profiles, key=lambda p: (p.last_name, p.first_name))

    def get_profile(self, profile_id: str) -> Profile:
        folder = self.root / profile_id

        metadata = folder / self.PROFILE_FILE

        if not metadata.exists():
            raise FileNotFoundError(profile_id)

        data = json.loads(metadata.read_text(encoding="utf-8"))

        return Profile(
            id=data["id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            company_name=data["company_name"],
            root=folder,
        )

    def load_document(
        self,
        profile: Profile,
        document: DocumentType,
    ) -> str:

        path = profile.root / document.filename

        if not path.exists():
            return ""

        return path.read_text(encoding="utf-8")

    def save_document(
        self,
        profile: Profile,
        document: DocumentType,
        text: str,
    ) -> None:

        path = profile.root / document.filename

        if not text.strip():
            if path.exists():
                path.unlink()
            return

        path.write_text(text, encoding="utf-8")



    def save_growth_plan(
        self,
        profile: Profile,
        content: str,
        title: str
    ) -> GrowthPlan:

        directory = self._growth_plan_directory(profile)

        filename = f"{title}.md"

        path = self._get_unique_path(directory, filename)

        path.write_text(
            content,
            encoding="utf-8"
        )

        return self._growth_plan_from_path(profile, path)

    def update_growth_plan(
        self,
        plan: GrowthPlan
    ) -> GrowthPlan:
        path = self._growth_plan_path_from_id(
            plan.profile_id,
            plan.id
        )

        path.write_text(
            plan.content,
            encoding="utf-8"
        )

        return self.load_growth_plan(
            self.get_profile(plan.profile_id),
            plan.id
        )

    def list_growth_plans(self, profile) -> list[GrowthPlan]:
        directory = self._growth_plan_directory(profile)

        return sorted(
            (
            self._growth_plan_from_path(profile, path)
            for path in directory.glob("*.md")
            ),
            key=lambda p: p.modified,
            reverse=True
        )

    def load_growth_plan(
        self,
        profile: Profile,
        plan_id: str
    ) -> GrowthPlan:

        path = self._growth_plan_path(profile, plan_id)

        return self._growth_plan_from_path(profile, path)


    def upload_document(
        self,
        profile: Profile,
        document: DocumentType,
        uploaded_file,
    ) -> None:

        if uploaded_file is None:
            return

        suffix = Path(uploaded_file.name).suffix.lower()

        if suffix == ".md":
            text = uploaded_file.getvalue().decode("utf-8")

        elif suffix == ".pdf":
            text = self._extract_pdf_text(uploaded_file)

        else:
            raise ValueError("Unsupported File type")

        self.save_document(profile, document, text)

    def validate_growth_profile(
        self,
        profile: Profile
    ) -> dict[DocumentType, bool]:

        return {
            document: (profile.root / document.filename).exists()
            for document in DocumentType
            if document != DocumentType.GROWTH_PLAN
        }

    def document_exists(
        self,
        profile: Profile,
        document: DocumentType
    ) -> bool:

        path = profile.root / document.filename
        return path.exists()

    # Helper methods

    def _save_profile_metadata(
        self,
        profile: Profile
    ) -> None:

        metadata = {
            "id": profile.id,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "company_name": profile.company_name
        }
        path = profile.root / self.PROFILE_FILE

        path.write_text(
            json.dumps(metadata, indent=4),
            encoding="utf-8"
        )

    @staticmethod
    def _extract_pdf_text(uploaded_file) -> str:

        reader = PdfReader(uploaded_file)

        pages = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        return "\n\n".join(pages)

    def _growth_plan_directory(self, profile: Profile):
        directory = profile.root / "GrowthPlans"
        directory.mkdir(exist_ok=True)
        return directory

    def _get_unique_path(self, directory: Path, filename: str) -> Path:

        path = directory / filename

        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix

        counter = 2

        while True:
            new_path = directory / f"{stem}_{counter}{suffix}"

            if not new_path.exists():
                return new_path

            counter +=1

    def _growth_plan_from_path(
        self,
        profile: Profile,
        path: Path
    ) -> GrowthPlan:

        stat = path.stat()

        return GrowthPlan(
            id=path.stem,
            profile_id=profile.id,
            title=path.stem.replace("_", " "),
            content=path.read_text(encoding="utf-8"),
            created=datetime.fromtimestamp(stat.st_ctime),
            modified=datetime.fromtimestamp(stat.st_mtime)
        )

    def _growth_plan_path(
        self,
        profile: Profile,
        plan_id: str
    ) -> Path:
        return self._growth_plan_directory(profile) / f"{plan_id}.md"

    def _growth_plan_path_from_id(
        self,
        profile_id: str,
        plan_id: str
    ) -> Path:
        profile = self.get_profile(profile_id)
        return self._growth_plan_directory(profile) / f"{plan_id}.md"

