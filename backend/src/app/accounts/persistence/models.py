from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from src.app.infrastructure.database_config import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    # Relationships. passive_deletes="all": deleting a user never touches the
    # children, so the foreign keys refuse to delete a user who still has data.
    search_configs = relationship(
        "SavedSearch", back_populates="user", passive_deletes="all"
    )
    price_alerts = relationship(
        "PriceAlert", back_populates="user", passive_deletes="all"
    )
    notification_logs = relationship(
        "NotificationLog", back_populates="user", passive_deletes="all"
    )
    subscription = relationship(
        "Subscription", back_populates="user", uselist=False, passive_deletes="all"
    )
