from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.brand import Brand

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPK, Base


class CarModel(Base):
    __tablename__ = "car_models"
    id: Mapped[UUIDPK]
    brand_id: Mapped[UUID] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120))
    brand: Mapped["Brand"] = relationship(lazy="raise")
    __table_args__ = (
        UniqueConstraint("brand_id", "slug"),
        Index("uq_car_models_brand_name", brand_id, func.lower(name), unique=True),
    )
