from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr

from app.models.enums import Role
from app.schemas.common import Schema


class UserRead(Schema):
    id: UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class RoleUpdate(Schema):
    role: Literal["user", "dealer"]
