from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.app.infrastructure.database_config import Base


class SearchExecutionLog(Base):
    """SearchExecutionLog SQLAlchemy model."""

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
    search_config = relationship("SearchConfig", back_populates="search_execution_logs")
