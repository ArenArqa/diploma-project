"""Ensure CHECK constraints reject partial NULL metric/history records."""

from alembic import op

revision = "0004_strict_checks"
down_revision = "0003_bookings"
branch_labels = None
depends_on = None

CHECKS = [
    (
        "listing_price_history",
        "ck_listing_price_history_history_consistency",
        "(reason = 'initial' AND old_price_amd IS NULL) OR "
        "(reason IN ('owner_update', 'admin_update') AND old_price_amd > 0 AND old_price_amd <> new_price_amd)",
        "(reason = 'initial' AND old_price_amd IS NULL) OR "
        "(reason IN ('owner_update', 'admin_update') AND old_price_amd IS NOT NULL "
        "AND old_price_amd > 0 AND old_price_amd <> new_price_amd)",
    ),
    (
        "market_snapshots",
        "ck_market_snapshots_quartiles_valid",
        "median_price_amd IS NULL OR (p25_price_amd > 0 AND "
        "p25_price_amd <= median_price_amd AND median_price_amd <= p75_price_amd)",
        "(median_price_amd IS NULL AND p25_price_amd IS NULL AND p75_price_amd IS NULL) OR "
        "(median_price_amd IS NOT NULL AND p25_price_amd IS NOT NULL AND p75_price_amd IS NOT NULL "
        "AND p25_price_amd > 0 AND p25_price_amd <= median_price_amd AND median_price_amd <= p75_price_amd)",
    ),
    (
        "market_snapshots",
        "ck_market_snapshots_car_days_valid",
        "occupied_car_days IS NULL OR (occupied_car_days >= 0 AND available_car_days >= occupied_car_days)",
        "(occupied_car_days IS NULL AND available_car_days IS NULL) OR "
        "(occupied_car_days IS NOT NULL AND available_car_days IS NOT NULL AND occupied_car_days >= 0 "
        "AND available_car_days >= occupied_car_days)",
    ),
]


def replace_checks(index):
    for table, name, old, new in CHECKS:
        op.drop_constraint(op.f(name), table, type_="check")
        op.create_check_constraint(op.f(name), table, [old, new][index])


def upgrade():
    replace_checks(1)


def downgrade():
    replace_checks(0)
