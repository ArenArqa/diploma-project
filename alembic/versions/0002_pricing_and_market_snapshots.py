"""0002 pricing and market snapshots. Frozen schema; independent of live ORM definitions."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_pricing"
down_revision = "0001_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "valuation_baselines",
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("base_price_amd", sa.Numeric(precision=14, scale=0), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("base_price_amd > 0", name=op.f("ck_valuation_baselines_baseline_positive")),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["car_models.id"],
            name=op.f("fk_valuation_baselines_model_id_car_models"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("model_id", name=op.f("pk_valuation_baselines")),
    )
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column(
            "listing_type",
            postgresql.ENUM("sale", "rent", name="listingtype", create_type=False),
            nullable=False,
        ),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("listing_count", sa.Integer(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("median_price_amd", sa.Numeric(precision=14, scale=0), nullable=True),
        sa.Column("p25_price_amd", sa.Numeric(precision=14, scale=0), nullable=True),
        sa.Column("p75_price_amd", sa.Numeric(precision=14, scale=0), nullable=True),
        sa.Column("sale_market_multiplier", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column("residual_log_mad", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("baseline_version", sa.String(length=32), nullable=True),
        sa.Column("occupied_car_days", sa.Integer(), nullable=True),
        sa.Column("available_car_days", sa.Integer(), nullable=True),
        sa.Column("occupancy_ratio", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.CheckConstraint(
            "(listing_type = 'sale' AND occupied_car_days IS NULL AND available_car_days IS NULL AND occupancy_ratio IS NULL) OR (listing_type = 'rent' AND sale_market_multiplier IS NULL AND residual_log_mad IS NULL AND baseline_version IS NULL)",
            name=op.f("ck_market_snapshots_metrics_match_type"),
        ),
        sa.CheckConstraint(
            "median_price_amd IS NULL OR (p25_price_amd > 0 AND p25_price_amd <= median_price_amd AND median_price_amd <= p75_price_amd)",
            name=op.f("ck_market_snapshots_quartiles_valid"),
        ),
        sa.CheckConstraint(
            "occupancy_ratio IS NULL OR occupancy_ratio BETWEEN 0 AND 1",
            name=op.f("ck_market_snapshots_occupancy_valid"),
        ),
        sa.CheckConstraint(
            "occupied_car_days IS NULL OR (occupied_car_days >= 0 AND available_car_days >= occupied_car_days)",
            name=op.f("ck_market_snapshots_car_days_valid"),
        ),
        sa.CheckConstraint(
            "residual_log_mad IS NULL OR residual_log_mad >= 0", name=op.f("ck_market_snapshots_mad_valid")
        ),
        sa.CheckConstraint(
            "sale_market_multiplier IS NULL OR sale_market_multiplier BETWEEN .85 AND 1.15",
            name=op.f("ck_market_snapshots_sale_factor_valid"),
        ),
        sa.CheckConstraint(
            "sample_count >= 0 AND listing_count >= sample_count",
            name=op.f("ck_market_snapshots_counts_valid"),
        ),
        sa.CheckConstraint("window_end >= window_start", name=op.f("ck_market_snapshots_window_valid")),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["car_models.id"],
            name=op.f("fk_market_snapshots_model_id_car_models"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_snapshots")),
        sa.UniqueConstraint("model_id", "listing_type", "as_of", name=op.f("uq_market_snapshots_model_id")),
    )
    op.create_index(
        "ix_snapshots_model_type_asof",
        "market_snapshots",
        ["model_id", "listing_type", sa.literal_column("as_of DESC")],
        unique=False,
    )
    op.create_table(
        "rental_quotes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("car_id", sa.Uuid(), nullable=False),
        sa.Column(
            "listing_type",
            postgresql.ENUM("sale", "rent", name="listingtype", create_type=False),
            nullable=False,
        ),
        sa.Column("renter_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "days",
            sa.SmallInteger(),
            sa.Computed("end_date - start_date + 1", persisted=True),
            nullable=False,
        ),
        sa.Column("base_daily_rate_amd", sa.Numeric(precision=14, scale=0), nullable=False),
        sa.Column("total_price_amd", sa.Numeric(precision=14, scale=0), nullable=False),
        sa.Column("market_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("pricing_version", sa.String(length=32), nullable=False),
        sa.Column("pricing_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("listing_type = 'rent'", name=op.f("ck_rental_quotes_rental_only")),
        sa.CheckConstraint(
            "base_daily_rate_amd > 0 AND total_price_amd > 0", name=op.f("ck_rental_quotes_amounts_positive")
        ),
        sa.CheckConstraint("days BETWEEN 1 AND 90", name=op.f("ck_rental_quotes_duration_valid")),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_rental_quotes_expiration_valid")),
        sa.ForeignKeyConstraint(
            ["listing_id", "car_id", "listing_type"],
            ["listings.id", "listings.car_id", "listings.listing_type"],
            name=op.f("fk_rental_quotes_listing_id_listings"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["market_snapshot_id"],
            ["market_snapshots.id"],
            name=op.f("fk_rental_quotes_market_snapshot_id_market_snapshots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["renter_id"], ["users.id"], name=op.f("fk_rental_quotes_renter_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rental_quotes")),
        sa.UniqueConstraint(
            "id", "car_id", "renter_id", "start_date", "end_date", name="uq_quote_booking_terms"
        ),
    )
    op.create_index(
        "ix_quotes_renter_created",
        "rental_quotes",
        ["renter_id", sa.literal_column("created_at DESC")],
        unique=False,
    )


def downgrade():
    op.drop_table("rental_quotes")
    op.drop_table("market_snapshots")
    op.drop_table("valuation_baselines")
