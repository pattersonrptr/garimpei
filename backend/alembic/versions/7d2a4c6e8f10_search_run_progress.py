"""Track the progress and outcome of each search run

A search run now has one execution log that the scrapers update while they
work: how many listings the sites returned, how many were checked, and how
many matched the search term. Runs left "running" by the old code (which
never closed its logs) are closed as failed.

Revision ID: 7d2a4c6e8f10
Revises: 5c1e8f3a9b20
Create Date: 2026-11-04 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d2a4c6e8f10"
down_revision: str | None = "5c1e8f3a9b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "search_execution_logs",
        sa.Column("listings_found", sa.Integer(), nullable=True),
    )
    op.add_column(
        "search_execution_logs",
        sa.Column("listings_checked", sa.Integer(), nullable=True),
    )
    op.execute(
        "UPDATE search_execution_logs "
        "SET status = 'failed', finished_at = started_at, "
        "error_message = 'Run was never closed (closed by migration)' "
        "WHERE status IN ('pending', 'running')"
    )


def downgrade() -> None:
    op.drop_column("search_execution_logs", "listings_checked")
    op.drop_column("search_execution_logs", "listings_found")
