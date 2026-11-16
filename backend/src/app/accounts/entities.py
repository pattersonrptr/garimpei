from dataclasses import dataclass
from datetime import datetime


@dataclass(kw_only=True)
class User:
    """A person with an account. The e-mail format is checked by the request
    schemas, not here."""

    id: int | None = None
    username: str
    email: str
    hashed_password: str | None = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
