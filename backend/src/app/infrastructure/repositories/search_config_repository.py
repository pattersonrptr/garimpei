from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.app.entities.search_config import SearchConfig as SearchConfigEntity
from src.app.infrastructure.database.models.search_config_model import (
    SearchConfig as SearchConfigModel,
)
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.interfaces.repositories.search_config_repository import (
    SearchConfigRepositoryInterface,
)


class SearchConfigRepository(SearchConfigRepositoryInterface):
    """SQLAlchemy implementation of SearchConfigRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: SearchConfigModel) -> SearchConfigEntity:
        """Convert a SearchConfig ORM model to a domain entity."""
        return SearchConfigEntity(
            id=model.id,
            search_term=model.search_term,
            is_active=model.is_active,
            frequency_days=model.frequency_days,
            preferred_time=model.preferred_time,
            search_metadata=model.search_metadata,
            user_id=model.user_id,
            source_website_ids=[sw.id for sw in model.source_websites],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _sync_source_websites(
        self, db_model: SearchConfigModel, source_website_ids: list[int]
    ) -> None:
        """Sync the M2M source_websites relationship from a list of IDs."""
        db_model.source_websites.clear()
        if source_website_ids:
            source_websites = (
                self.db.query(SourceWebsiteModel)
                .filter(SourceWebsiteModel.id.in_(source_website_ids))
                .all()
            )
            db_model.source_websites.extend(source_websites)

    def create(self, search_config: SearchConfigEntity) -> SearchConfigEntity:
        """Persist a new search config and return it with assigned id."""
        db_search_config = SearchConfigModel(
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

    def get_by_id(self, search_config_id: int) -> SearchConfigEntity | None:
        """Retrieve a search config by its primary key."""
        db_record = (
            self.db.query(SearchConfigModel)
            .options(joinedload(SearchConfigModel.source_websites))
            .filter(SearchConfigModel.id == search_config_id)
            .first()
        )
        return self._to_entity(db_record) if db_record else None

    def get_by_user_id(self, user_id: int) -> list[SearchConfigEntity]:
        """Return all search configs for a given user."""
        records = (
            self.db.query(SearchConfigModel)
            .options(joinedload(SearchConfigModel.source_websites))
            .filter(SearchConfigModel.user_id == user_id)
            .all()
        )
        return [self._to_entity(r) for r in records]

    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> SearchConfigEntity | None:
        """Return a search config matching term + user (for uniqueness check)."""
        db_record = (
            self.db.query(SearchConfigModel)
            .filter(
                SearchConfigModel.search_term == search_term,
                SearchConfigModel.user_id == user_id,
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
    ) -> tuple[list[SearchConfigEntity], int]:
        """Return a paginated list of all search configs and the total count."""
        query = self.db.query(SearchConfigModel).options(
            joinedload(SearchConfigModel.source_websites)
        )
        if user_id is not None:
            query = query.filter(SearchConfigModel.user_id == user_id)

        total = query.count()

        if sort_by and hasattr(SearchConfigModel, sort_by):
            order_column = getattr(SearchConfigModel, sort_by)
            query = query.order_by(
                desc(order_column) if sort_order == "desc" else asc(order_column)
            )

        records = query.offset(offset).limit(limit).all()
        return [self._to_entity(r) for r in records], total

    def update(
        self, search_config_id: int, search_config: SearchConfigEntity
    ) -> SearchConfigEntity | None:
        """Update a search config. Returns updated entity or None if not found."""
        db_record = (
            self.db.query(SearchConfigModel)
            .options(joinedload(SearchConfigModel.source_websites))
            .filter(SearchConfigModel.id == search_config_id)
            .first()
        )
        if not db_record:
            return None

        db_record.search_term = search_config.search_term
        db_record.is_active = search_config.is_active
        db_record.frequency_days = search_config.frequency_days
        db_record.preferred_time = search_config.preferred_time
        db_record.search_metadata = search_config.search_metadata
        db_record.user_id = search_config.user_id

        self._sync_source_websites(db_record, search_config.source_website_ids)

        self.db.commit()
        self.db.refresh(db_record)
        return self._to_entity(db_record)

    def delete(self, search_config_id: int) -> bool:
        """Delete a search config by id. Returns True if deleted, False if not found."""
        db_record = (
            self.db.query(SearchConfigModel)
            .filter(SearchConfigModel.id == search_config_id)
            .first()
        )
        if not db_record:
            return False
        self.db.delete(db_record)
        self.db.commit()
        return True
