"""Book price alerts: an alert can target a book and a condition

Phase 4c. A keyword alert keeps working as before (both columns null). A book
alert has `canonical_product_id` (the book) and `condition` (new, used or
any) and matches any store's offer for that book.

Revision ID: d7e4a9c2b158
Revises: c4d2f8a61b37
Create Date: 2026-11-11 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e4a9c2b158"
down_revision: str | None = "c4d2f8a61b37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "price_alerts",
        sa.Column("canonical_product_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "price_alerts", sa.Column("condition", sa.String(length=10), nullable=True)
    )
    op.create_foreign_key(
        "fk_price_alerts_canonical_product_id",
        "price_alerts",
        "canonical_products",
        ["canonical_product_id"],
        ["id"],
    )
    op.create_index(
        "ix_price_alert_canonical_product_id",
        "price_alerts",
        ["canonical_product_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_price_alert_canonical_product_id", table_name="price_alerts")
    op.drop_constraint(
        "fk_price_alerts_canonical_product_id", "price_alerts", type_="foreignkey"
    )
    op.drop_column("price_alerts", "condition")
    op.drop_column("price_alerts", "canonical_product_id")
