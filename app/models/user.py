from sqlalchemy import Boolean, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base, Created, Updated
from app.models.enums import Role


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUIDPK]
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(default=Role.user, server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[Created]
    updated_at: Mapped[Updated]
    __table_args__ = (Index("uq_users_email_lower", func.lower(email), unique=True),)
