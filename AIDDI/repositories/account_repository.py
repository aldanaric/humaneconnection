from pathlib import Path

from models.access_level import AccessLevel
from models.account import Account
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

    def list_accounts(self) -> list[Account]:

        accounts = []

        for folder in self.root.iterdir():

            if not folder.is_dir():
                continue

            metadata = folder / self.ACCOUNT_FILE

            if not metadata.exists():
                continue

            data = json.loads(metadata.read_text())

            accounts.append(
                Account(
                    id=data["id"],
                    account_name=data["account_name"],
                    password_hash=data["password_hash"],
                    access_level=AccessLevel(data["access_level"]),
                    root=folder
                )
            )

        return sorted(accounts, key=lambda a:a.account_name.lower())

    def get_account(self, account_id: str) -> Account:

        folder = self.root / account_id

        metadata = folder / self.ACCOUNT_FILE

        if not metadata.exists():
            raise FileNotFoundError(account_id)

        data = json.loads(metadata.read_text())

        return Account(
            id=data["id"],
            account_name=data["account_name"],
            password_hash=data["password_hash"],
            access_level=AccessLevel(data["access_level"]),
            root=folder
        )

    def get_account_by_name(
        self,
        account_name: str,
    ) -> Account | None:

        for account in self.list_accounts():

            if account.account_name.lower() == account_name.lower():
                return account

        return None

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

        self._save_account_metadata(account)



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


    def account_exists(
        self,
        account_name: str,
    ) -> bool:

        return self.get_account_by_name(account_name) is not None

    def delete_account(
        self,
        account_id: str,
    ) -> None:

        folder = self.root / account_id

        if folder.exists():
            shutil.rmtree(folder)


    def get_profiles_root(
        self,
        account: Account
    ) -> Path:
        return account.root / "Profiles"

    # private helper

    def _save_account_metadata(
        self,
        account: Account,
    ) -> None:

        metadata = {
            "id": account.id,
            "account_name": account.account_name,
            "password_hash": account.password_hash,
            "access_level": account.access_level,
        }

        path = account.root / self.ACCOUNT_FILE

        path.write_text(
            json.dumps(metadata, indent=4),
            encoding="utf-8"
        )



