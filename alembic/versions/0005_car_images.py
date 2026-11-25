"""Optional public image URL for physical cars."""

import sqlalchemy as sa

from alembic import op

revision = "0005_car_images"
down_revision = "0004_strict_checks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cars", sa.Column("image_url", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("cars", "image_url")
