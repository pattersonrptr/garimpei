from datetime import UTC, datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
)
from sqlalchemy.orm import relationship

from src.app.infrastructure.database.models.search_config_source_website_model import (
    search_config_source_website,
)
from src.app.infrastructure.database_config import Base


class SearchConfig(Base):
    """SearchConfig SQLAlchemy model."""

    __tablename__ = "search_configs"

    id = Column(Integer, primary_key=True)
    search_term = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    frequency_days = Column(Integer, default=1, nullable=False)
    preferred_time = Column(Time, default=time(0, 0), nullable=False)
    search_metadata = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="search_configs")
    source_websites = relationship(
        "SourceWebsite",
        secondary=search_config_source_website,
        back_populates="search_configs",
    )
    search_execution_logs = relationship(
        "SearchExecutionLog", back_populates="search_config"
    )
    price_alerts = relationship("PriceAlert", back_populates="search_config")

    __table_args__ = (
        Index("ix_search_config_term", search_term),
        Index("ix_search_config_active", is_active),
    )
