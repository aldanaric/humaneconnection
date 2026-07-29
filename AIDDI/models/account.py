from dataclasses import dataclass
from pathlib import Path

from models.access_level import AccessLevel


@dataclass
class Account:
    id: str
    account_name: str
    password_hash: str
    access_level: AccessLevel

