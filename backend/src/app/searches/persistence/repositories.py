from dataclasses import fields

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.app.alerts.persistence.models import (
    PriceAlert as PriceAlertModel,
)
from src.app.infrastructure.database.text_match import title_contains
from src.app.searches.entities import SavedSearch, SearchRun
from src.app.searches.persistence.models import SavedSearch as SavedSearchModel
from src.app.searches.persistence.models import SearchRun as SearchRunModel
from src.app.searches.ports import (
    SavedSearchRepositoryInterface,
    SearchRunRepositoryInterface,
)
from src.app.stores.persistence.models import Store as StoreModel

# The fields an update writes (dates are left to the model).
_UPDATABLE = (
    "search_term",
    "is_active",
    "frequency_days",
    "preferred_time",
    "search_metadata",
    "user_id",
)


class SavedSearchRepository(SavedSearchRepositoryInterface):
    """SQLAlchemy implementation of SavedSearchRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: SavedSearchModel) -> SavedSearch:
        """Convert a SearchConfig ORM model to a domain entity."""
        columns = {
            f.name: getattr(model, f.name)
            for f in fields(SavedSearch)
            if f.name != "source_website_ids"
        }
        return SavedSearch(
            **columns, source_website_ids=[sw.id for sw in model.source_websites]
        )

    def _sync_source_websites(
        self, db_model: SavedSearchModel, source_website_ids: list[int]
    ) -> None:
        """Sync the M2M source_websites relationship from a list of IDs."""
        db_model.source_websites.clear()
        if source_website_ids:
            source_websites = (
                self.db.query(StoreModel)
                .filter(StoreModel.id.in_(source_website_ids))
                .all()
            )
            db_model.source_websites.extend(source_websites)

    def create(self, search_config: SavedSearch) -> SavedSearch:
        """Persist a new search config and return it with assigned id."""
        db_search_config = SavedSearchModel(
            search_term=search_config.search_term,
            is_active=search_config.is_active,
            frequency_days=search_config.frequency_days,
            preferred_time=search_config.preferred_time,
            search_metadata=search_config.search_metadata,
            user_id=search_config.user_id,
        )
        self.db.add(db_search_config)
        self.db.flush()  # get the id before syncing M2M

        self._sync_source_websites(db_search_config, search_config.source_website_ids)

        self.db.commit()
        self.db.refresh(db_search_config)
        return self._to_entity(db_search_config)

    def get_by_id(self, search_config_id: int) -> SavedSearch | None:
        """Retrieve a search config by its primary key."""
        db_record = (
            self.db.query(SavedSearchModel)
            .options(joinedload(SavedSearchModel.source_websites))
            .filter(SavedSearchModel.id == search_config_id)
            .first()
        )
        return self._to_entity(db_record) if db_record else None

    def get_by_user_id(self, user_id: int) -> list[SavedSearch]:
        """Return all search configs for a given user."""
        records = (
            self.db.query(SavedSearchModel)
            .options(joinedload(SavedSearchModel.source_websites))
            .filter(SavedSearchModel.user_id == user_id)
            .all()
        )
        return [self._to_entity(r) for r in records]

    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> SavedSearch | None:
        """Return a search config matching term + user (for uniqueness check)."""
        db_record = (
            self.db.query(SavedSearchModel)
            .filter(
                SavedSearchModel.search_term == search_term,
                SavedSearchModel.user_id == user_id,
            )
            .first()
        )
        return self._to_entity(db_record) if db_record else None

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        user_id: int | None = None,
        search_term: str | None = None,
    ) -> tuple[list[SavedSearch], int]:
        """Return a paginated list of all search configs and the total count."""
        query = self.db.query(SavedSearchModel).options(
            joinedload(SavedSearchModel.source_websites)
        )
        if user_id is not None:
            query = query.filter(SavedSearchModel.user_id == user_id)
        if search_term:
            query = query.filter(
                title_contains(SavedSearchModel.search_term, search_term)
            )

        total = query.count()

        if sort_by and hasattr(SavedSearchModel, sort_by):
            order_column = getattr(SavedSearchModel, sort_by)
            query = query.order_by(
                desc(order_column) if sort_order == "desc" else asc(order_column)
            )
        query = query.order_by(desc(SavedSearchModel.id))  # newest first

        records = query.offset(offset).limit(limit).all()
        return [self._to_entity(r) for r in records], total

    def update(
        self, search_config_id: int, search_config: SavedSearch
    ) -> SavedSearch | None:
        """Update a search config. Returns updated entity or None if not found."""
        db_record = (
            self.db.query(SavedSearchModel)
            .options(joinedload(SavedSearchModel.source_websites))
            .filter(SavedSearchModel.id == search_config_id)
            .first()
        )
        if not db_record:
            return None

        for name in _UPDATABLE:
            setattr(db_record, name, getattr(search_config, name))

        self._sync_source_websites(db_record, search_config.source_website_ids)

        self.db.commit()
        self.db.refresh(db_record)
        return self._to_entity(db_record)

    def delete(self, search_config_id: int) -> bool:
        """Delete a search config by id. Returns True if deleted, False if not found."""
        db_record = (
            self.db.query(SavedSearchModel)
            .filter(SavedSearchModel.id == search_config_id)
            .first()
        )
        if not db_record:
            return False
        # The run history goes with the search; soft-deleted alerts that still
        # point at it are detached (live alerts are checked by the use case).
        self.db.query(SearchRunModel).filter(
            SearchRunModel.search_config_id == search_config_id
        ).delete(synchronize_session=False)
        self.db.query(PriceAlertModel).filter(
            PriceAlertModel.search_config_id == search_config_id,
            PriceAlertModel.deleted_at.is_not(None),
        ).update({PriceAlertModel.search_config_id: None}, synchronize_session=False)
        self.db.delete(db_record)
        self.db.commit()
        return True


class SearchRunRepository(SearchRunRepositoryInterface):
    """SQLAlchemy implementation of SearchRunRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: SearchRunModel) -> SearchRun:
        return SearchRun(**{f.name: getattr(model, f.name) for f in fields(SearchRun)})

    def create(self, search_execution_log: SearchRun) -> SearchRun:
        """Persist a new search execution log."""
        db_log = SearchRunModel(
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

    def update(self, search_execution_log_id: int, changes: dict) -> SearchRun | None:
        """Apply field changes to a log; returns None if it does not exist."""
        db_log = (
            self.db.query(SearchRunModel)
            .filter(SearchRunModel.id == search_execution_log_id)
            .first()
        )
        if not db_log:
            return None
        for field, value in changes.items():
            setattr(db_log, field, value)
        self.db.commit()
        self.db.refresh(db_log)
        return self._to_entity(db_log)

    def get_by_id(self, search_execution_log_id: int) -> SearchRun | None:
        """Retrieve a search execution log by its primary key."""
        db_log = (
            self.db.query(SearchRunModel)
            .filter(SearchRunModel.id == search_execution_log_id)
            .first()
        )
        return self._to_entity(db_log) if db_log else None

    def get_by_search_config_id(self, search_config_id: int) -> list[SearchRun]:
        """Return all logs for a given search config, ordered by started_at desc."""
        records = (
            self.db.query(SearchRunModel)
            .filter(SearchRunModel.search_config_id == search_config_id)
            .order_by(desc(SearchRunModel.started_at))
            .all()
        )
        return [self._to_entity(r) for r in records]

    def get_latest_by_search_config_id(self, search_config_id: int) -> SearchRun | None:
        """Return the most recent log for a given search config, or None."""
        record = (
            self.db.query(SearchRunModel)
            .filter(SearchRunModel.search_config_id == search_config_id)
            .order_by(desc(SearchRunModel.started_at))
            .first()
        )
        return self._to_entity(record) if record else None

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[SearchRun], int]:
        """Return a paginated list of all search execution logs and the total count."""
        query = self.db.query(SearchRunModel)

        total = query.count()

        if sort_by and hasattr(SearchRunModel, sort_by):
            order_column = getattr(SearchRunModel, sort_by)
            query = query.order_by(
                desc(order_column) if sort_order == "desc" else asc(order_column)
            )
        else:
            query = query.order_by(desc(SearchRunModel.started_at))

        records = query.limit(limit).offset(offset).all()
        return [self._to_entity(r) for r in records], total

    def delete(self, search_execution_log_id: int) -> bool:
        """Delete a search execution log by id."""
        db_log = (
            self.db.query(SearchRunModel)
            .filter(SearchRunModel.id == search_execution_log_id)
            .first()
        )
        if not db_log:
            return False
        self.db.delete(db_log)
        self.db.commit()
        return True
