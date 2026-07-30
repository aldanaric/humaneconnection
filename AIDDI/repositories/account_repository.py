from pathlib import Path

from models.access_level import AccessLevel
from models.account import Account
import json
import uuid
import shutil
import bcrypt
from services.database import connect
from psycopg.errors import UniqueViolation


class AccountRepository:

    def create_account(
        self,
        account_name: str,
        password: str,
        access_level: AccessLevel = AccessLevel.USER
    ) -> Account:

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        try:
            with connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO accounts (account_name, password_hash, access_level)
                        VALUES (%s, %s, %s)
                        RETURNING id, account_name, password_hash, access_level
                        """,
                        (account_name, password_hash, access_level.value)
                    )
                    row = cursor.fetchone()
                conn.commit()
        except UniqueViolation:
            raise ValueError("Account with this username already exists")

        return self._account_from_row(row)

    def list_accounts(self) -> list[Account]:

        with connect() as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        account_name,
                        password_hash,
                        access_level
                    FROM accounts
                    ORDER BY LOWER(account_name)
                    """
                )
                rows = cursor.fetchall()

        return [
            self._account_from_row(row)
            for row in rows
        ]

    def get_account(self, account_id: str) -> Account:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        account_name,
                        password_hash,
                        access_level
                    FROM accounts
                    WHERE id = %s
                    """,
                    (account_id,)
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("Account not found")

        return self._account_from_row(row)


    def get_account_by_name(
        self,
        account_name: str,
    ) -> Account | None:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, account_name, password_hash, access_level
                    FROM accounts
                    WHERE account_name = %s
                    """,
                    (account_name,)
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("Account not found")

        return self._account_from_row(row)

    def authenticate(
        self,
        account_name: str,
        password: str,
    ) -> Account | None:

        account = self.get_account_by_name(account_name)

        if account is None:
            return None

        valid = bcrypt.checkpw(
            password.encode("utf-8"),
            account.password_hash.encode("utf-8")
        )

        if not valid:
            return None

        return account

    def update_account(
        self,
        account: Account,
    ) -> None:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE accounts
                    SET
                        account_name = %s,
                        password_hash = %s,
                        access_level = %s
                    WHERE id = %s""",
                    (
                        account.account_name,
                        account.password_hash,
                        account.access_level.value,
                        account.id,
                    ),
                )
            conn.commit()

    def change_password(
        self,
        account: Account,
        new_password: str,
    ) -> None:

        account.password_hash = bcrypt.hashpw(
            new_password.encode(),
            bcrypt.gensalt()
        ).decode()

        self.update_account(account)

    def update_access_level(
        self,
        account: Account,
        new_access_level: AccessLevel
    ) -> None:

        account.access_level = new_access_level

        self.update_account(account)


    def account_exists(
        self,
        account_name: str,
    ) -> bool:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM accounts
                        WHERE account_name = %s
                    )
                    """,
                    (account_name,)
                )
                return cursor.fetchone()[0]

    def delete_account(
        self,
        account_id: str,
    ) -> None:

        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM accounts
                    WHERE id = %s""",
                    (account_id,)
                )


    # private helper

    @staticmethod
    def _account_from_row(row) -> Account:
        return Account(
            id=str(row[0]),
            account_name=row[1],
            password_hash=row[2],
            access_level=AccessLevel(row[3])
        )

