from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base


class Brand(Base):
    __tablename__ = "brands"
    id: Mapped[UUIDPK]
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    __table_args__ = (Index("uq_brands_name_lower", func.lower(name), unique=True),)
