from repositories.account_repository import AccountRepository
from models.access_level import AccessLevel

repo = AccountRepository()

if repo.get_account_by_name("InitialAdmin"):
    print("Admin already exists")
else:
    repo.create_account(
        "InitialAdmin",
        "AIDDI",
        AccessLevel.ADMIN,
    )
    print("Created admin account")
