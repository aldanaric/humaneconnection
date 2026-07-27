from dataclasses import dataclass
from datetime import datetime

from models.document_type import DocumentType


@dataclass
class ProfileDocument:
    id: str
    name: str
    modified: datetime
