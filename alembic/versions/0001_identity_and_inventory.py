"""0001 identity and inventory. Frozen schema; independent of live ORM definitions."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_inventory"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    postgresql.ENUM("confirmed", "cancelled", name="bookingstatus", create_type=False).create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("poor", "fair", "good", "excellent", name="condition", create_type=False).create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(
        "gasoline", "diesel", "hybrid", "electric", "lpg", name="fueltype", create_type=False
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("active", "archived", "sold", name="listingstatus", create_type=False).create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("sale", "rent", name="listingtype", create_type=False).create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("user", "dealer", "admin", name="role", create_type=False).create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("manual", "automatic", name="transmission", create_type=False).create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("user", "dealer", "admin", name="role", create_type=False),
            server_default="user",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index("uq_users_email_lower", "users", [sa.literal_column("lower(email)")], unique=True)
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brands")),
        sa.UniqueConstraint("slug", name=op.f("uq_brands_slug")),
    )
    op.create_index("uq_brands_name_lower", "brands", [sa.literal_column("lower(name)")], unique=True)
    op.create_table(
        "car_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(
            ["brand_id"], ["brands.id"], name=op.f("fk_car_models_brand_id_brands"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_car_models")),
        sa.UniqueConstraint("brand_id", "slug", name=op.f("uq_car_models_brand_id")),
    )
    op.create_index(
        "uq_car_models_brand_name", "car_models", ["brand_id", sa.literal_column("lower(name)")], unique=True
    )
    op.create_table(
        "cars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("vin", sa.String(length=17), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("mileage_km", sa.Integer(), nullable=False),
        sa.Column(
            "fuel_type",
            postgresql.ENUM(
                "gasoline", "diesel", "hybrid", "electric", "lpg", name="fueltype", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "transmission",
            postgresql.ENUM("manual", "automatic", name="transmission", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "condition",
            postgresql.ENUM("poor", "fair", "good", "excellent", name="condition", create_type=False),
            nullable=False,
        ),
        sa.Column("color", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("vin ~ '^[A-HJ-NPR-Z0-9]{17}$'", name=op.f("ck_cars_vin_format")),
        sa.CheckConstraint("mileage_km >= 0", name=op.f("ck_cars_mileage_nonnegative")),
        sa.CheckConstraint("year BETWEEN 1900 AND 2100", name=op.f("ck_cars_year_range")),
        sa.ForeignKeyConstraint(
            ["model_id"], ["car_models.id"], name=op.f("fk_cars_model_id_car_models"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_cars_owner_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cars")),
        sa.UniqueConstraint("vin", name=op.f("uq_cars_vin")),
    )
    op.create_index("ix_cars_fuel_year", "cars", ["fuel_type", "year", "id"], unique=False)
    op.create_index(
        "ix_cars_model_year_mileage", "cars", ["model_id", "year", "mileage_km", "id"], unique=False
    )
    op.create_index(
        "ix_cars_owner_created",
        "cars",
        ["owner_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("car_id", sa.Uuid(), nullable=False),
        sa.Column(
            "listing_type",
            postgresql.ENUM("sale", "rent", name="listingtype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("active", "archived", "sold", name="listingstatus", create_type=False),
            server_default="active",
            nullable=False,
        ),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("price_amd", sa.Numeric(precision=14, scale=0), nullable=False),
        sa.Column(
            "price_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status <> 'sold' OR listing_type = 'sale'", name=op.f("ck_listings_sold_only_sale")
        ),
        sa.CheckConstraint("price_amd > 0", name=op.f("ck_listings_price_positive")),
        sa.ForeignKeyConstraint(
            ["car_id"], ["cars.id"], name=op.f("fk_listings_car_id_cars"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listings")),
        sa.UniqueConstraint("id", "car_id", "listing_type", name="uq_listing_identity"),
    )
    op.create_index(op.f("ix_listings_car_id"), "listings", ["car_id"], unique=False)
    op.create_index(
        "ix_listings_type_created",
        "listings",
        ["listing_type", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_listings_type_price",
        "listings",
        ["listing_type", "price_amd", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_one_active_listing_per_car",
        "listings",
        ["car_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "listing_price_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("old_price_amd", sa.Numeric(precision=14, scale=0), nullable=True),
        sa.Column("new_price_amd", sa.Numeric(precision=14, scale=0), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(reason = 'initial' AND old_price_amd IS NULL) OR (reason IN ('owner_update', 'admin_update') AND old_price_amd > 0 AND old_price_amd <> new_price_amd)",
            name=op.f("ck_listing_price_history_history_consistency"),
        ),
        sa.CheckConstraint("new_price_amd > 0", name=op.f("ck_listing_price_history_new_price_positive")),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name=op.f("fk_listing_price_history_changed_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
            name=op.f("fk_listing_price_history_listing_id_listings"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listing_price_history")),
    )
    op.create_index(
        "ix_history_listing_changed",
        "listing_price_history",
        ["listing_id", sa.literal_column("changed_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )


def downgrade():
    op.drop_table("listing_price_history")
    op.drop_table("listings")
    op.drop_table("cars")
    op.drop_table("car_models")
    op.drop_table("brands")
    op.drop_table("users")
    postgresql.ENUM(name="transmission", create_type=False).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="role", create_type=False).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="listingtype", create_type=False).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="listingstatus", create_type=False).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="fueltype", create_type=False).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="condition", create_type=False).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="bookingstatus", create_type=False).drop(op.get_bind(), checkfirst=True)
