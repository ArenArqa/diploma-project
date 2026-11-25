from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Updated


class ValuationBaseline(Base):
    __tablename__ = "valuation_baselines"
    model_id: Mapped[UUID] = mapped_column(ForeignKey("car_models.id", ondelete="RESTRICT"), primary_key=True)
    base_price_amd: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    source: Mapped[str] = mapped_column(String(40), default="synthetic_demo")
    version: Mapped[str] = mapped_column(String(32), default="demo-v1")
    updated_at: Mapped[Updated]
    __table_args__ = (CheckConstraint("base_price_amd > 0", name="baseline_positive"),)
