"""Deleting a listing clears it from the notification logs

A sent e-mail is history: when its listing is deleted, the log stays and its
`product_id` becomes null. The catalog's product repository used to clear it
by hand before deleting (reaching into alerts' tables); the database does it
now (ON DELETE SET NULL).

Revision ID: e5f1a7c3d904
Revises: d7e4a9c2b158
Create Date: 2026-11-16 15:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f1a7c3d904"
down_revision: str | None = "d7e4a9c2b158"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Postgres' default name for the baseline's unnamed constraint.
FK = "notification_logs_product_id_fkey"


def upgrade() -> None:
    op.drop_constraint(FK, "notification_logs", type_="foreignkey")
    op.create_foreign_key(
        FK,
        "notification_logs",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(FK, "notification_logs", type_="foreignkey")
    op.create_foreign_key(FK, "notification_logs", "products", ["product_id"], ["id"])
