"""Add canonical products and their identifiers

A canonical product is the product itself (a book, with its ISBN-13),
independent of any store. Today's `products` rows are store offers; the new
nullable `products.canonical_product_id` links an offer to its canonical
product once matched. Nothing existing changes: offers, price history and
alerts keep working, and old rows simply stay unlinked.

Revision ID: a1c3e5b79d02
Revises: 8e3b5d7f9a21
Create Date: 2026-11-09 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c3e5b79d02"
down_revision: str | None = "8e3b5d7f9a21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "attributes",
            sa.JSON(),
            nullable=False,
            comment="Category-specific data (author, publisher, ...)",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_canonical_products_category", "canonical_products", ["category"]
    )

    op.create_table(
        "product_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "canonical_product_id",
            sa.Integer(),
            sa.ForeignKey("canonical_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("value", sa.String(64), nullable=False),
        sa.UniqueConstraint("kind", "value", name="uq_product_identifier_kind_value"),
    )
    op.create_index(
        "ix_product_identifiers_canonical_product_id",
        "product_identifiers",
        ["canonical_product_id"],
    )

    op.add_column(
        "products",
        sa.Column(
            "canonical_product_id",
            sa.Integer(),
            nullable=True,
            comment="The product this offer is for, once matched",
        ),
    )
    op.create_foreign_key(
        "fk_products_canonical_product_id",
        "products",
        "canonical_products",
        ["canonical_product_id"],
        ["id"],
    )
    op.create_index(
        "ix_products_canonical_product_id", "products", ["canonical_product_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_products_canonical_product_id", table_name="products")
    op.drop_constraint(
        "fk_products_canonical_product_id", "products", type_="foreignkey"
    )
    op.drop_column("products", "canonical_product_id")
    op.drop_index(
        "ix_product_identifiers_canonical_product_id", table_name="product_identifiers"
    )
    op.drop_table("product_identifiers")
    op.drop_index("ix_canonical_products_category", table_name="canonical_products")
    op.drop_table("canonical_products")
