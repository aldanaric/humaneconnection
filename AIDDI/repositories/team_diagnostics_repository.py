"""PostgreSQL repository for Team Diagnostics teams, members, and reports.

Assumes `accounts` and `profiles` already exist in Postgres. This module only
owns the Team Diagnostics tables (`teams`, `team_members`,
`team_diagnostic_reports`).
"""
from __future__ import annotations

import json
from typing import Any

from models.team import Team
from models.team_diagnostic_report import TeamDiagnosticReport
from services.database import connect


class TeamDiagnosticsRepository:
    def create_team(
        self,
        account_id: str,
        name: str,
        display_name: str,
        company_info: str = "",
        team_info: str = "",
    ) -> Team:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO teams (
                        account_id, name, display_name, company_info, team_info
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, account_id, name, display_name, company_info,
                              team_info, created_at, updated_at
                    """,
                    (
                        account_id,
                        name,
                        display_name,
                        company_info,
                        team_info,
                    ),
                )
                row = cursor.fetchone()
            conn.commit()
        return self._team_from_row(row, member_profile_ids=[])

    def get_team_by_name(self, account_id: str, name: str) -> Team | None:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, account_id, name, display_name, company_info,
                           team_info, created_at, updated_at
                    FROM teams
                    WHERE account_id = %s AND name = %s
                    """,
                    (account_id, name),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                members = self._list_member_ids(cursor, str(row[0]))
        return self._team_from_row(row, member_profile_ids=members)

    def get_team(self, account_id: str, team_id: str) -> Team | None:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, account_id, name, display_name, company_info,
                           team_info, created_at, updated_at
                    FROM teams
                    WHERE account_id = %s AND id = %s
                    """,
                    (account_id, team_id),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                members = self._list_member_ids(cursor, str(row[0]))
        return self._team_from_row(row, member_profile_ids=members)

    def list_teams(self, account_id: str) -> list[Team]:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, account_id, name, display_name, company_info,
                           team_info, created_at, updated_at
                    FROM teams
                    WHERE account_id = %s
                    ORDER BY display_name ASC, name ASC
                    """,
                    (account_id,),
                )
                rows = cursor.fetchall()
                teams: list[Team] = []
                for row in rows:
                    members = self._list_member_ids(cursor, str(row[0]))
                    teams.append(
                        self._team_from_row(row, member_profile_ids=members)
                    )
        return teams

    def update_team_context(
        self,
        account_id: str,
        name: str,
        *,
        display_name: str | None = None,
        company_info: str | None = None,
        team_info: str | None = None,
    ) -> Team:
        team = self.get_team_by_name(account_id, name)
        if team is None:
            raise FileNotFoundError(name)

        next_display = (
            display_name.strip()
            if display_name and display_name.strip()
            else team.display_name
        )
        next_company = (
            company_info if company_info is not None else team.company_info
        )
        next_team_info = team_info if team_info is not None else team.team_info

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teams
                    SET display_name = %s,
                        company_info = %s,
                        team_info = %s,
                        updated_at = NOW()
                    WHERE account_id = %s AND name = %s
                    RETURNING id, account_id, name, display_name, company_info,
                              team_info, created_at, updated_at
                    """,
                    (
                        next_display,
                        next_company,
                        next_team_info,
                        account_id,
                        name,
                    ),
                )
                row = cursor.fetchone()
                members = self._list_member_ids(cursor, str(row[0]))
            conn.commit()
        return self._team_from_row(row, member_profile_ids=members)

    def add_member(
        self,
        account_id: str,
        team_name: str,
        profile_id: str,
    ) -> Team:
        team = self.get_team_by_name(account_id, team_name)
        if team is None:
            raise FileNotFoundError(team_name)

        members = list(team.member_profile_ids or [])
        if profile_id in members:
            raise ValueError("That profile is already on this team.")

        position = len(members)
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO team_members (team_id, profile_id, position)
                    VALUES (%s, %s, %s)
                    """,
                    (team.id, profile_id, position),
                )
            conn.commit()

        refreshed = self.get_team_by_name(account_id, team_name)
        assert refreshed is not None
        return refreshed

    def remove_member(
        self,
        account_id: str,
        team_name: str,
        profile_id: str,
    ) -> Team:
        team = self.get_team_by_name(account_id, team_name)
        if team is None:
            raise FileNotFoundError(team_name)

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM team_members
                    WHERE team_id = %s AND profile_id = %s
                    """,
                    (team.id, profile_id),
                )
                cursor.execute(
                    """
                    SELECT profile_id
                    FROM team_members
                    WHERE team_id = %s
                    ORDER BY position ASC, created_at ASC
                    """,
                    (team.id,),
                )
                remaining = [str(row[0]) for row in cursor.fetchall()]
                for index, remaining_id in enumerate(remaining):
                    cursor.execute(
                        """
                        UPDATE team_members
                        SET position = %s, updated_at = NOW()
                        WHERE team_id = %s AND profile_id = %s
                        """,
                        (index, team.id, remaining_id),
                    )
            conn.commit()

        refreshed = self.get_team_by_name(account_id, team_name)
        assert refreshed is not None
        return refreshed

    def list_member_profile_ids(self, account_id: str, team_name: str) -> list[str]:
        team = self.get_team_by_name(account_id, team_name)
        if team is None:
            return []
        return list(team.member_profile_ids or [])

    def create_report(
        self,
        account_id: str,
        team_name: str,
        *,
        title: str,
        content: str,
        prompt_template_name: str = "default",
        audience: str = "Facilitator",
        requested_outputs: list[str] | None = None,
        used_humane_connection: bool = False,
    ) -> TeamDiagnosticReport:
        team = self.get_team_by_name(account_id, team_name)
        if team is None:
            raise FileNotFoundError(team_name)

        outputs = requested_outputs or []
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO team_diagnostic_reports (
                        team_id,
                        account_id,
                        title,
                        content,
                        prompt_template_name,
                        audience,
                        requested_outputs,
                        used_humane_connection
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    RETURNING id, team_id, account_id, title, content,
                              prompt_template_name, audience, requested_outputs,
                              used_humane_connection, created_at, updated_at
                    """,
                    (
                        team.id,
                        account_id,
                        title,
                        content,
                        prompt_template_name,
                        audience,
                        json.dumps(outputs),
                        used_humane_connection,
                    ),
                )
                row = cursor.fetchone()
            conn.commit()
        return self._report_from_row(row)

    def update_report_content(
        self,
        account_id: str,
        report_id: str,
        content: str,
    ) -> TeamDiagnosticReport:
        return self.update_report(
            account_id,
            report_id,
            content=content,
        )

    def update_report(
        self,
        account_id: str,
        report_id: str,
        *,
        content: str | None = None,
        title: str | None = None,
    ) -> TeamDiagnosticReport:
        existing = self.get_report(account_id, report_id)
        if existing is None:
            raise FileNotFoundError(report_id)

        next_content = content if content is not None else existing.content
        next_title = title.strip() if title is not None else existing.title
        if not next_title:
            raise ValueError("Report title is required.")

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE team_diagnostic_reports
                    SET content = %s,
                        title = %s,
                        updated_at = NOW()
                    WHERE account_id = %s AND id = %s
                    RETURNING id, team_id, account_id, title, content,
                              prompt_template_name, audience, requested_outputs,
                              used_humane_connection, created_at, updated_at
                    """,
                    (next_content, next_title, account_id, report_id),
                )
                row = cursor.fetchone()
            conn.commit()

        if row is None:
            raise FileNotFoundError(report_id)
        return self._report_from_row(row)

    def get_report(
        self,
        account_id: str,
        report_id: str,
    ) -> TeamDiagnosticReport | None:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, team_id, account_id, title, content,
                           prompt_template_name, audience, requested_outputs,
                           used_humane_connection, created_at, updated_at
                    FROM team_diagnostic_reports
                    WHERE account_id = %s AND id = %s
                    """,
                    (account_id, report_id),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return self._report_from_row(row)

    def delete_report(self, account_id: str, report_id: str) -> None:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM team_diagnostic_reports
                    WHERE account_id = %s AND id = %s
                    """,
                    (account_id, report_id),
                )
                if cursor.rowcount == 0:
                    raise FileNotFoundError(report_id)
            conn.commit()

    def list_reports(
        self,
        account_id: str,
        team_name: str,
    ) -> list[TeamDiagnosticReport]:
        team = self.get_team_by_name(account_id, team_name)
        if team is None:
            return []

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, team_id, account_id, title, content,
                           prompt_template_name, audience, requested_outputs,
                           used_humane_connection, created_at, updated_at
                    FROM team_diagnostic_reports
                    WHERE team_id = %s AND account_id = %s
                    ORDER BY updated_at DESC
                    """,
                    (team.id, account_id),
                )
                rows = cursor.fetchall()
        return [self._report_from_row(row) for row in rows]

    def get_latest_report(
        self,
        account_id: str,
        team_name: str,
        prompt_template_name: str | None = None,
    ) -> TeamDiagnosticReport | None:
        reports = self.list_reports(account_id, team_name)
        if not reports:
            return None
        if prompt_template_name:
            for report in reports:
                if report.prompt_template_name == prompt_template_name:
                    return report
        return reports[0]

    def create_report_always(
        self,
        account_id: str,
        team_name: str,
        *,
        content: str,
        prompt_template_name: str = "default",
        title: str | None = None,
        audience: str = "Facilitator",
        requested_outputs: list[str] | None = None,
        used_humane_connection: bool = False,
    ) -> TeamDiagnosticReport:
        """Always insert a new report (keeps history)."""
        resolved_title = title or f"Team Diagnostics ({prompt_template_name})"
        return self.create_report(
            account_id,
            team_name,
            title=resolved_title,
            content=content,
            prompt_template_name=prompt_template_name,
            audience=audience,
            requested_outputs=requested_outputs,
            used_humane_connection=used_humane_connection,
        )

    def save_or_update_latest_report(
        self,
        account_id: str,
        team_name: str,
        *,
        content: str,
        prompt_template_name: str = "default",
        title: str | None = None,
        audience: str = "Facilitator",
        requested_outputs: list[str] | None = None,
        used_humane_connection: bool = False,
    ) -> TeamDiagnosticReport:
        """Deprecated path: prefer create_report_always for new generations."""
        return self.create_report_always(
            account_id,
            team_name,
            content=content,
            prompt_template_name=prompt_template_name,
            title=title,
            audience=audience,
            requested_outputs=requested_outputs,
            used_humane_connection=used_humane_connection,
        )

    @staticmethod
    def _list_member_ids(cursor: Any, team_id: str) -> list[str]:
        cursor.execute(
            """
            SELECT profile_id
            FROM team_members
            WHERE team_id = %s
            ORDER BY position ASC, created_at ASC
            """,
            (team_id,),
        )
        return [str(row[0]) for row in cursor.fetchall()]

    @staticmethod
    def _team_from_row(
        row: tuple,
        member_profile_ids: list[str] | None = None,
    ) -> Team:
        return Team(
            id=str(row[0]),
            account_id=str(row[1]),
            name=row[2],
            display_name=row[3],
            company_info=row[4] or "",
            team_info=row[5] or "",
            created_at=row[6],
            updated_at=row[7],
            member_profile_ids=member_profile_ids or [],
        )

    @staticmethod
    def _report_from_row(row: tuple) -> TeamDiagnosticReport:
        outputs = row[7]
        if isinstance(outputs, str):
            outputs = json.loads(outputs)
        elif outputs is None:
            outputs = []
        return TeamDiagnosticReport(
            id=str(row[0]),
            team_id=str(row[1]),
            account_id=str(row[2]),
            title=row[3],
            content=row[4],
            prompt_template_name=row[5],
            audience=row[6],
            requested_outputs=list(outputs),
            used_humane_connection=bool(row[8]),
            created_at=row[9],
            updated_at=row[10],
        )
