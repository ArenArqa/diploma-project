"""0003 booking constraints. Frozen schema; independent of live ORM definitions."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_bookings"
down_revision = "0002_pricing"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("car_id", sa.Uuid(), nullable=False),
        sa.Column("renter_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "period",
            postgresql.DATERANGE(),
            sa.Computed("daterange(start_date, end_date, '[]')", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("confirmed", "cancelled", name="bookingstatus", create_type=False),
            server_default="confirmed",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        postgresql.ExcludeConstraint(
            (sa.column("car_id"), "="),
            (sa.column("period"), "&&"),
            where=sa.text("status = 'confirmed'"),
            using="gist",
            name="bookings_no_overlap",
        ),
        sa.CheckConstraint(
            "(status = 'confirmed' AND cancelled_at IS NULL AND cancelled_by IS NULL AND cancellation_reason IS NULL) OR (status = 'cancelled' AND cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL)",
            name=op.f("ck_bookings_cancellation_consistent"),
        ),
        sa.CheckConstraint(
            "end_date >= start_date AND end_date - start_date + 1 <= 90",
            name=op.f("ck_bookings_booking_dates_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by"], ["users.id"], name=op.f("fk_bookings_cancelled_by_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["car_id"], ["cars.id"], name=op.f("fk_bookings_car_id_cars"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["quote_id", "car_id", "renter_id", "start_date", "end_date"],
            [
                "rental_quotes.id",
                "rental_quotes.car_id",
                "rental_quotes.renter_id",
                "rental_quotes.start_date",
                "rental_quotes.end_date",
            ],
            name=op.f("fk_bookings_quote_id_rental_quotes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["renter_id"], ["users.id"], name=op.f("fk_bookings_renter_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
        sa.UniqueConstraint("quote_id", name=op.f("uq_bookings_quote_id")),
    )
    op.create_index("ix_bookings_car_status_end", "bookings", ["car_id", "status", "end_date"], unique=False)
    op.create_index(
        "ix_bookings_renter_created",
        "bookings",
        ["renter_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )


def downgrade():
    op.drop_table("bookings")
