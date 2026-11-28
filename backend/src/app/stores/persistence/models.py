from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from src.app.infrastructure.database_config import Base


class Store(Base):
    """Store SQLAlchemy model (table source_websites)."""

    __tablename__ = "source_websites"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    base_url = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    # passive_deletes="all": deleting a store never touches its offers, so the
    # foreign key refuses to delete a store that still has offers.
    products = relationship(
        "Product", back_populates="source_website", passive_deletes="all"
    )
    search_configs = relationship(
        "SavedSearch",
        secondary="search_config_source_website",
        back_populates="source_websites",
    )
    price_alerts = relationship(
        "PriceAlert",
        secondary="price_alert_source_website",
        back_populates="source_websites",
    )
