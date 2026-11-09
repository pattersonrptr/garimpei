"""Deactivate the marketplaces whose scrapers are broken

The OLX and Mercado Livre scrapers returned nothing in local tests on
2026-11-03 (the sites changed or block them). Offering them made new alerts
look fine while they could never find anything. An administrator can turn them
back on in Admin > Source websites once the scrapers are fixed.

Revision ID: 8e3b5d7f9a21
Revises: 7d2a4c6e8f10
Create Date: 2026-11-04 10:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8e3b5d7f9a21"
down_revision: str | None = "7d2a4c6e8f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BROKEN = "('olx', 'mercado_livre')"


def upgrade() -> None:
    op.execute(f"UPDATE source_websites SET is_active = false WHERE name IN {BROKEN}")


def downgrade() -> None:
    op.execute(f"UPDATE source_websites SET is_active = true WHERE name IN {BROKEN}")
