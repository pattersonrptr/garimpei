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
    Table,
)
from sqlalchemy.orm import relationship

from src.app.infrastructure.database_config import Base

price_alert_source_website = Table(
    "price_alert_source_website",
    Base.metadata,
    Column(
        "price_alert_id",
        Integer,
        ForeignKey("price_alerts.id"),
        primary_key=True,
    ),
    Column(
        "source_website_id",
        Integer,
        ForeignKey("source_websites.id"),
        primary_key=True,
    ),
)


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


class NotificationLog(Base):
    """NotificationLog SQLAlchemy model for tracking sent email notifications."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True)
    price_alert_id = Column(Integer, ForeignKey("price_alerts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    email_to = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    status = Column(String(20), default="sent", nullable=False)
    error_message = Column(String(1000), nullable=True)
    sent_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    price_alert = relationship("PriceAlert", back_populates="notification_logs")
    user = relationship("User", back_populates="notification_logs")
    product = relationship("Product")

    __table_args__ = (
        Index("ix_notification_log_price_alert_id", price_alert_id),
        Index("ix_notification_log_user_id", user_id),
        Index("ix_notification_log_sent_at", sent_at),
    )
