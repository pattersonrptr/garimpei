"""Add a search text to canonical products

The public search looks for a term in a book's title and authors, ignoring
case and accents. Authors live in the `attributes` JSON, where accents are
stored escaped (\u00e1) next to a long synopsis, so the JSON cannot be
searched as text. `search_text` keeps the title and authors folded
(lowercase, no accents); the repository writes it on create, and this
migration fills it in for the books that already exist.

Revision ID: c4d2f8a61b37
Revises: a1c3e5b79d02
Create Date: 2026-11-10 23:00:00.000000

"""

import json
import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d2f8a61b37"
down_revision: str | None = "a1c3e5b79d02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def fold_text(text: str) -> str:
    """A frozen copy of text_match.fold_text, so this migration never changes."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def search_text(title: str, attributes) -> str:
    if isinstance(attributes, str):
        attributes = json.loads(attributes)
    authors = (attributes or {}).get("authors", [])
    return fold_text(" ".join([title, *authors]))


def upgrade() -> None:
    op.add_column(
        "canonical_products",
        sa.Column(
            "search_text",
            sa.Text(),
            nullable=False,
            server_default="",
            comment="Title and authors, lowercase and without accents",
        ),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, title, attributes FROM canonical_products")
    ).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE canonical_products SET search_text = :text WHERE id = :id"),
            {"text": search_text(row.title, row.attributes), "id": row.id},
        )


def downgrade() -> None:
    op.drop_column("canonical_products", "search_text")
