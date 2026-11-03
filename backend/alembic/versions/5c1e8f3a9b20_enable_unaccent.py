"""Enable the unaccent extension

Search terms are matched against product titles ignoring accents
("microsservicos" finds "Microsserviços"); see
src/app/infrastructure/database/text_match.py.

Revision ID: 5c1e8f3a9b20
Revises: 02608ed9b827
Create Date: 2026-11-03 20:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c1e8f3a9b20"
down_revision: str | None = "02608ed9b827"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS unaccent")
