from enum import Enum

class AccessLevel(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READ_ONLY = "read_only"
