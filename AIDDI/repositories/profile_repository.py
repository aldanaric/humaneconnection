import json
import uuid
from pathlib import Path

from pypdf import PdfReader
from pathlib import Path
from datetime import datetime

from models.profile import Profile
from models.document_type import DocumentType
from models.growth_plan import GrowthPlan
from models.profile_document import ProfileDocument

from services.database import connect


class ProfileRepository:
    """Repository for creating, loading, and saving Growth Plan profiles"""

    def __init__(self, account_id: str):
        self.account_id = account_id

    def create_profile(
        self,
        first_name: str,
        last_name: str,
        company_name: str
    ) -> Profile:
        """Create a new profile"""
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO profiles (
                        account_id,
                        first_name,
                        last_name,
                        company_name
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, first_name, last_name, company_name""",
                    (self.account_id, first_name, last_name, company_name)
                )
                row = cursor.fetchone()
            conn.commit()

        return self._profile_from_row(row)

    def list_profiles(
        self,
    ) -> list[Profile]:
        """Return every profile"""

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, first_name, last_name, company_name
                    FROM profiles
                    WHERE account_id = %s""",
                    (self.account_id,)
                )
                rows = cursor.fetchall()

        return [
            self._profile_from_row(row)
            for row in rows
        ]

    def get_profile(self, profile_id: str) -> Profile:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, first_name, last_name, company_name
                    FROM profiles
                    WHERE id = %s
                    AND account_id = %s""",
                    (profile_id, self.account_id)
                )
                row = cursor.fetchone()

        return self._profile_from_row(row)

    def load_document(
        self,
        profile: Profile,
        document: DocumentType,
    ) -> str:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT content
                    FROM profile_documents
                    WHERE profile_id = %s
                    AND document_type = %s
                    """,
                    (
                        profile.id,
                        document.value
                    )
                )

                row = cursor.fetchone()

        return row[0] if row else ""

    def save_document(
        self,
        profile: Profile,
        document: DocumentType,
        text: str,
    ) -> None:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO profile_documents
                    (
                        profile_id,
                        document_type,
                        content
                    )
                    VALUES (%s, %s, %s)

                    ON CONFLICT
                    (
                    profile_id,
                    document_type
                    )

                    DO UPDATE SET
                        content = EXCLUDED.content
                    """,
                    (profile.id,
                     document.value,
                     text),
                )
            conn.commit()



    def save_growth_plan(
        self,
        profile: Profile,
        content: str,
        title: str
    ) -> GrowthPlan:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO growth_plans
                    (
                    profile_id,
                    account_id,
                    title,
                    content
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, profile_id, title, content, created_at, updated_at""",
                    (profile.id, self.account_id, title, content)
                )
                row = cursor.fetchone()
            conn.commit()

        return self._growth_plan_from_row(row)


    def update_growth_plan(
        self,
        plan: GrowthPlan
    ) -> GrowthPlan:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE growth_plans
                    SET content = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    AND account_id = %s""",
                    (plan.content, plan.id, self.account_id)
                )
            conn.commit()
        return self.load_growth_plan(
            self.get_profile(plan.profile_id),
            plan.id
        )

    def list_growth_plans(self, profile) -> list[GrowthPlan]:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        profile_id,
                        title,
                        content,
                        created_at,
                        updated_at
                    FROM growth_plans
                    WHERE profile_id = %s
                    ORDER BY updated_at DESC""",
                    (profile.id,)
                )
                rows = cursor.fetchall()

        return [
            self._growth_plan_from_row(row)
            for row in rows
        ]

    def load_growth_plan(
        self,
        profile: Profile,
        plan_id: str
    ) -> GrowthPlan:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        profile_id,
                        title,
                        content,
                        created_at,
                        updated_at
                    FROM growth_plans
                    WHERE profile_id = %s
                    AND id = %s""",
                    (profile.id, plan_id)
                )
                row = cursor.fetchone()

        if row is None:
            raise FileNotFoundError(plan_id)

        return self._growth_plan_from_row(row)


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
            document: self.document_exists(profile, document)
            for document in DocumentType
            if document != DocumentType.GROWTH_PLAN
        }

    def document_exists(
        self,
        profile: Profile,
        document: DocumentType
    ) -> bool:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM profile_documents
                        WHERE profile_id = %s
                        AND document_type = %s
                    )
                    """,
                    (profile.id, document.value)
                )
                return cursor.fetchone()[0]

    def list_documents(
        self,
        profile: Profile
    ) -> list[ProfileDocument]:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        document_type,
                        updated_at
                    FROM profile_documents
                    WHERE profile_id = %s
                    ORDER BY updated_at DESC""",
                    (profile.id,)
                )

                rows = cursor.fetchall()
        return [
            ProfileDocument(
                id=str(row[0]),
                name=row[1].replace("_", " "),
                modified=row[2]
            )
            for row in rows
        ]

    def load_profile_document(
        self,
        profile: Profile,
        document: ProfileDocument
    ) -> str:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT content
                    FROM profile_documents
                    WHERE profile_id = %s
                    AND id = %s""",
                    (profile.id, document.id)
                )
                row = cursor.fetchone()
        return row[0] if row else ""

    # Helper methods
    @staticmethod
    def _profile_from_row(row) -> Profile:

        return Profile(
            id=str(row[0]),
            first_name=row[1],
            last_name=row[2],
            company_name=row[3],
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

    @staticmethod
    def _growth_plan_from_row(row) -> GrowthPlan:

        return GrowthPlan(
            id=str(row[0]),
            profile_id=row[1],
            title=row[2],
            content=row[3],
            created=row[4],
            modified=row[5]
        )


