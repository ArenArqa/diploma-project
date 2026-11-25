from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base
from app.models.enums import ListingType


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    id: Mapped[UUIDPK]
    model_id: Mapped[UUID] = mapped_column(ForeignKey("car_models.id", ondelete="RESTRICT"))
    listing_type: Mapped[ListingType]
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_start: Mapped[date]
    window_end: Mapped[date]
    listing_count: Mapped[int]
    sample_count: Mapped[int]
    median_price_amd: Mapped[Decimal | None] = mapped_column(Numeric(14, 0))
    p25_price_amd: Mapped[Decimal | None] = mapped_column(Numeric(14, 0))
    p75_price_amd: Mapped[Decimal | None] = mapped_column(Numeric(14, 0))
    sale_market_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    residual_log_mad: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    baseline_version: Mapped[str | None] = mapped_column(String(32))
    occupied_car_days: Mapped[int | None]
    available_car_days: Mapped[int | None]
    occupancy_ratio: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    __table_args__ = (
        UniqueConstraint("model_id", "listing_type", "as_of"),
        CheckConstraint("window_end >= window_start", name="window_valid"),
        CheckConstraint("sample_count >= 0 AND listing_count >= sample_count", name="counts_valid"),
        CheckConstraint(
            "(median_price_amd IS NULL AND p25_price_amd IS NULL AND p75_price_amd IS NULL) OR "
            "(median_price_amd IS NOT NULL AND p25_price_amd IS NOT NULL AND p75_price_amd IS NOT NULL "
            "AND p25_price_amd > 0 AND "
            "p25_price_amd <= median_price_amd AND median_price_amd <= p75_price_amd)",
            name="quartiles_valid",
        ),
        CheckConstraint(
            "sale_market_multiplier IS NULL OR sale_market_multiplier BETWEEN .85 AND 1.15",
            name="sale_factor_valid",
        ),
        CheckConstraint("residual_log_mad IS NULL OR residual_log_mad >= 0", name="mad_valid"),
        CheckConstraint("occupancy_ratio IS NULL OR occupancy_ratio BETWEEN 0 AND 1", name="occupancy_valid"),
        CheckConstraint(
            "(occupied_car_days IS NULL AND available_car_days IS NULL) OR "
            "(occupied_car_days IS NOT NULL AND available_car_days IS NOT NULL AND occupied_car_days >= 0 AND "
            "available_car_days >= occupied_car_days)",
            name="car_days_valid",
        ),
        CheckConstraint(
            "(listing_type = 'sale' AND occupied_car_days IS NULL AND "
            "available_car_days IS NULL AND occupancy_ratio IS NULL) OR "
            "(listing_type = 'rent' AND sale_market_multiplier IS NULL AND "
            "residual_log_mad IS NULL AND baseline_version IS NULL)",
            name="metrics_match_type",
        ),
        Index("ix_snapshots_model_type_asof", model_id, "listing_type", text("as_of DESC")),
    )
