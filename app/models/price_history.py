from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base, Created


class PriceHistory(Base):
    __tablename__ = "listing_price_history"
    id: Mapped[UUIDPK]
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    old_price_amd: Mapped[Decimal | None] = mapped_column(Numeric(14, 0))
    new_price_amd: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[Created]
    __table_args__ = (
        CheckConstraint("new_price_amd > 0", name="new_price_positive"),
        CheckConstraint(
            "(reason = 'initial' AND old_price_amd IS NULL) OR "
            "(reason IN ('owner_update', 'admin_update') AND old_price_amd IS NOT NULL AND old_price_amd > 0 "
            "AND old_price_amd <> new_price_amd)",
            name="history_consistency",
        ),
        Index("ix_history_listing_changed", listing_id, text("changed_at DESC"), text("id DESC")),
    )
