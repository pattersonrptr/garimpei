from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from src.app.entities.search_execution_log import (
    SearchExecutionLog as SearchExecutionLogEntity,
)
from src.app.infrastructure.database.models.search_execution_log_model import (
    SearchExecutionLog as SearchExecutionLogModel,
)
from src.app.interfaces.repositories.search_execution_log_repository import (
    SearchExecutionLogRepositoryInterface,
)


class SearchExecutionLogRepository(SearchExecutionLogRepositoryInterface):
    """SQLAlchemy implementation of SearchExecutionLogRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: SearchExecutionLogModel) -> SearchExecutionLogEntity:
        return SearchExecutionLogEntity(
            id=model.id,
            search_config_id=model.search_config_id,
            status=model.status,
            results_count=model.results_count,
            listings_found=model.listings_found,
            listings_checked=model.listings_checked,
            error_message=model.error_message,
            started_at=model.started_at,
            finished_at=model.finished_at,
        )

    def create(
        self, search_execution_log: SearchExecutionLogEntity
    ) -> SearchExecutionLogEntity:
        """Persist a new search execution log."""
        db_log = SearchExecutionLogModel(
            search_config_id=search_execution_log.search_config_id,
            status=search_execution_log.status,
            results_count=search_execution_log.results_count,
            listings_found=search_execution_log.listings_found,
            listings_checked=search_execution_log.listings_checked,
            error_message=search_execution_log.error_message,
            started_at=search_execution_log.started_at,
            finished_at=search_execution_log.finished_at,
        )
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return self._to_entity(db_log)

    def update(
        self, search_execution_log_id: int, changes: dict
    ) -> SearchExecutionLogEntity | None:
        """Apply field changes to a log; returns None if it does not exist."""
        db_log = (
            self.db.query(SearchExecutionLogModel)
            .filter(SearchExecutionLogModel.id == search_execution_log_id)
            .first()
        )
        if not db_log:
            return None
        for field, value in changes.items():
            setattr(db_log, field, value)
        self.db.commit()
        self.db.refresh(db_log)
        return self._to_entity(db_log)

    def get_by_id(
        self, search_execution_log_id: int
    ) -> SearchExecutionLogEntity | None:
        """Retrieve a search execution log by its primary key."""
        db_log = (
            self.db.query(SearchExecutionLogModel)
            .filter(SearchExecutionLogModel.id == search_execution_log_id)
            .first()
        )
        return self._to_entity(db_log) if db_log else None

    def get_by_search_config_id(
        self, search_config_id: int
    ) -> list[SearchExecutionLogEntity]:
        """Return all logs for a given search config, ordered by started_at desc."""
        records = (
            self.db.query(SearchExecutionLogModel)
            .filter(SearchExecutionLogModel.search_config_id == search_config_id)
            .order_by(desc(SearchExecutionLogModel.started_at))
            .all()
        )
        return [self._to_entity(r) for r in records]

    def get_latest_by_search_config_id(
        self, search_config_id: int
    ) -> SearchExecutionLogEntity | None:
        """Return the most recent log for a given search config, or None."""
        record = (
            self.db.query(SearchExecutionLogModel)
            .filter(SearchExecutionLogModel.search_config_id == search_config_id)
            .order_by(desc(SearchExecutionLogModel.started_at))
            .first()
        )
        return self._to_entity(record) if record else None

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[SearchExecutionLogEntity], int]:
        """Return a paginated list of all search execution logs and the total count."""
        query = self.db.query(SearchExecutionLogModel)

        total = query.count()

        if sort_by and hasattr(SearchExecutionLogModel, sort_by):
            order_column = getattr(SearchExecutionLogModel, sort_by)
            query = query.order_by(
                desc(order_column) if sort_order == "desc" else asc(order_column)
            )
        else:
            query = query.order_by(desc(SearchExecutionLogModel.started_at))

        records = query.limit(limit).offset(offset).all()
        return [self._to_entity(r) for r in records], total

    def delete(self, search_execution_log_id: int) -> bool:
        """Delete a search execution log by id."""
        db_log = (
            self.db.query(SearchExecutionLogModel)
            .filter(SearchExecutionLogModel.id == search_execution_log_id)
            .first()
        )
        if not db_log:
            return False
        self.db.delete(db_log)
        self.db.commit()
        return True
