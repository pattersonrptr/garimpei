from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship

from src.app.catalog.entities import ProductCondition
from src.app.infrastructure.database_config import Base


class Product(Base):
    """Product SQLAlchemy model."""

    __tablename__ = "products"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Identification
    url = Column(Text, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    source_product_code = Column(
        String(50),
        index=True,
        nullable=True,
        comment="Unique identifier from the source website (e.g., olx-1365326779)",
    )

    # Content
    description = Column(Text, nullable=True)
    image_urls = Column(Text, nullable=True, comment="Image URLs separated by commas")

    # Location
    city = Column(String(255), nullable=True)
    state = Column(String(50), nullable=True)

    # Product details
    condition = Column(
        SQLAlchemyEnum(ProductCondition),
        default=ProductCondition.UNDETERMINED,
        nullable=False,
    )
    seller_name = Column(String(255), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)

    # Source information
    source_website_id = Column(
        Integer,
        ForeignKey("source_websites.id"),
        index=True,
        nullable=False,
        comment="Foreign key to source website",
    )
    source_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional source-specific data in JSON format",
    )
    canonical_product_id = Column(
        Integer,
        ForeignKey("canonical_products.id"),
        index=True,
        nullable=True,
        comment="The product this offer is for, once matched",
    )

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    source_website = relationship("SourceWebsite", back_populates="products")
    price_history = relationship(
        "PriceHistory",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class PriceHistory(Base):
    """PriceHistory SQLAlchemy model — append-only price records per product."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to the tracked product",
    )
    price = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Recorded price at this point in time",
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    product = relationship("Product", back_populates="price_history")

    __table_args__ = (
        Index("ix_price_history_product_created", "product_id", "created_at"),
    )


class CanonicalProduct(Base):
    """CanonicalProduct SQLAlchemy model: the product itself, not a store's offer."""

    __tablename__ = "canonical_products"

    id = Column(Integer, primary_key=True)
    category = Column(String(30), index=True, nullable=False)
    title = Column(String(500), nullable=False)
    attributes = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Category-specific data (author, publisher, ...)",
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    identifiers = relationship(
        "ProductIdentifier",
        back_populates="canonical_product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProductIdentifier(Base):
    """ProductIdentifier SQLAlchemy model: a code (ISBN-13, EAN, ...) of a product."""

    __tablename__ = "product_identifiers"

    id = Column(Integer, primary_key=True)
    canonical_product_id = Column(
        Integer,
        ForeignKey("canonical_products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind = Column(String(20), nullable=False)
    value = Column(String(64), nullable=False)

    canonical_product = relationship("CanonicalProduct", back_populates="identifiers")

    __table_args__ = (
        UniqueConstraint("kind", "value", name="uq_product_identifier_kind_value"),
    )
