from pathlib import Path

from models.access_level import AccessLevel, Account
import json
import uuid
import shutil
import bcrypt


class AccountRepository:

    ACCOUNT_FILE = "account.json"

    def __init__(self):
        self.root = Path("data/Accounts")
        self.root.mkdir(parents=True, exist_ok=True)


    def create_account(
        self,
        account_name: str,
        password: str,
        access_level: AccessLevel = AccessLevel.USER
    ) -> Account:

        if self.account_exists(account_name):
            raise ValueError("Account already exists")

        account_id = str(uuid.uuid4())

        folder = self.root / account_id
        folder.mkdir(parents=True)

        (folder / "Profiles").mkdir(exist_ok=True)

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        account = Account(
            id=account_id,
            account_name=account_name,
            password_hash=password_hash,
            access_level=access_level,
            root=folder
        )

        self._save_account_metadata(account)


        return account

