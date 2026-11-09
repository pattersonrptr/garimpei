from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from src.app.infrastructure.database_config import Base


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
