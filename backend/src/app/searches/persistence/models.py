"""Saved searches' ORM models: search configs, their stores and their runs."""

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
    Table,
    Time,
)
from sqlalchemy.orm import relationship

from src.app.infrastructure.database_config import Base

search_config_source_website = Table(
    "search_config_source_website",
    Base.metadata,
    Column(
        "search_config_id",
        Integer,
        ForeignKey("search_configs.id"),
        primary_key=True,
    ),
    Column(
        "source_website_id",
        Integer,
        ForeignKey("source_websites.id"),
        primary_key=True,
    ),
)


class SavedSearch(Base):
    """A saved search (table search_configs)."""

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
        "Store",
        secondary=search_config_source_website,
        back_populates="search_configs",
    )
    search_execution_logs = relationship("SearchRun", back_populates="search_config")
    price_alerts = relationship("PriceAlert", back_populates="search_config")

    __table_args__ = (
        Index("ix_search_config_term", search_term),
        Index("ix_search_config_active", is_active),
    )


class SearchRun(Base):
    """One run of a saved search (table search_execution_logs)."""

    __tablename__ = "search_execution_logs"

    id = Column(Integer, primary_key=True)
    search_config_id = Column(Integer, ForeignKey("search_configs.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    results_count = Column(Integer, nullable=True)
    listings_found = Column(Integer, nullable=True)
    listings_checked = Column(Integer, nullable=True)
    error_message = Column(String(1000), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    search_config = relationship("SavedSearch", back_populates="search_execution_logs")
