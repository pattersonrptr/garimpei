from datetime import UTC, datetime

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.interfaces.repositories.source_website_repository import (
    SourceWebsiteRepositoryInterface,
)
from src.app.stores.entities import Store


class SourceWebsiteRepository(SourceWebsiteRepositoryInterface):
    """SQLAlchemy implementation of SourceWebsiteRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, source_website: Store) -> Store:
        """Create a new source website in the database."""
        db_source_website = SourceWebsiteModel(
            name=source_website.name,
            base_url=source_website.base_url,
            is_active=source_website.is_active,
            created_at=source_website.created_at,
            updated_at=source_website.updated_at,
        )
        self.db.add(db_source_website)
        self.db.commit()
        self.db.refresh(db_source_website)
        return self._to_entity(db_source_website)

    def get_by_id(self, source_website_id: int) -> Store | None:
        """Retrieve a source website by ID."""
        db_source_website = (
            self.db.query(SourceWebsiteModel)
            .filter(SourceWebsiteModel.id == source_website_id)
            .first()
        )
        return self._to_entity(db_source_website) if db_source_website else None

    def get_by_name(self, name: str) -> Store | None:
        """Retrieve a source website by its unique name."""
        db_source_website = (
            self.db.query(SourceWebsiteModel)
            .filter(SourceWebsiteModel.name == name)
            .first()
        )
        return self._to_entity(db_source_website) if db_source_website else None

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[Store], int]:
        """Retrieve all source websites with pagination and sorting."""
        query = self.db.query(SourceWebsiteModel)

        # Total count before pagination
        total = query.count()

        # Apply sorting
        if sort_by and hasattr(SourceWebsiteModel, sort_by):
            order_column = getattr(SourceWebsiteModel, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        else:
            # Default: most recently created first
            query = query.order_by(desc(SourceWebsiteModel.created_at))

        # Apply pagination
        source_websites = query.limit(limit).offset(offset).all()

        return [self._to_entity(sw) for sw in source_websites], total

    def update(self, source_website_id: int, source_website: Store) -> Store | None:
        """Update an existing source website."""
        db_source_website = (
            self.db.query(SourceWebsiteModel)
            .filter(SourceWebsiteModel.id == source_website_id)
            .first()
        )
        if not db_source_website:
            return None

        try:
            db_source_website.name = source_website.name
            db_source_website.base_url = source_website.base_url
            db_source_website.is_active = source_website.is_active
            db_source_website.updated_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(db_source_website)
            return self._to_entity(db_source_website)
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, source_website_id: int) -> bool:
        """Delete a source website from the database."""
        db_source_website = (
            self.db.query(SourceWebsiteModel)
            .filter(SourceWebsiteModel.id == source_website_id)
            .first()
        )
        if not db_source_website:
            return False

        try:
            self.db.delete(db_source_website)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def _to_entity(self, source_website_model: SourceWebsiteModel) -> Store:
        """Convert SourceWebsiteModel to Store."""
        return Store(
            id=source_website_model.id,
            name=source_website_model.name,
            base_url=source_website_model.base_url,
            is_active=source_website_model.is_active,
            created_at=source_website_model.created_at,
            updated_at=source_website_model.updated_at,
        )
