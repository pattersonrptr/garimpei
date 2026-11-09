from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from src.app.infrastructure.database.models.price_alert_source_website_model import (
    price_alert_source_website,
)
from src.app.infrastructure.database_config import Base


class PriceAlert(Base):
    """PriceAlert SQLAlchemy model."""

    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    search_term = Column(String(255), nullable=False)
    max_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    frequency_minutes = Column(Integer, default=60, nullable=False)
    last_triggered_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    search_config_id = Column(Integer, ForeignKey("search_configs.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at = Column(DateTime, nullable=True, default=None)

    # Relationships
    user = relationship("User", back_populates="price_alerts")
    search_config = relationship("SearchConfig", back_populates="price_alerts")
    source_websites = relationship(
        "SourceWebsite",
        secondary=price_alert_source_website,
        back_populates="price_alerts",
    )
    notification_logs = relationship("NotificationLog", back_populates="price_alert")

    __table_args__ = (
        Index("ix_price_alert_term", search_term),
        Index("ix_price_alert_active", is_active),
        Index("ix_price_alert_user_id", user_id),
        Index("ix_price_alert_search_config_id", search_config_id),
        Index("ix_price_alert_deleted_at", deleted_at),
    )
