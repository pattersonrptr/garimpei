from dataclasses import asdict, fields
from datetime import UTC, datetime

from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.stores.entities import Store
from src.app.stores.persistence.models import Store as StoreModel
from src.app.stores.ports import StoreHasOffersError, StoreRepositoryInterface

# The fields an update writes (the controller passes no dates).
_UPDATABLE = ("name", "base_url", "is_active")


class StoreRepository(StoreRepositoryInterface):
    """SQLAlchemy implementation of StoreRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, source_website: Store) -> Store:
        """Create a new source website in the database."""
        columns = asdict(source_website)
        del columns["id"]
        db_source_website = StoreModel(**columns)
        self.db.add(db_source_website)
        self.db.commit()
        self.db.refresh(db_source_website)
        return self._to_entity(db_source_website)

    def get_by_id(self, source_website_id: int) -> Store | None:
        """Retrieve a source website by ID."""
        db_source_website = (
            self.db.query(StoreModel).filter(StoreModel.id == source_website_id).first()
        )
        return self._to_entity(db_source_website) if db_source_website else None

    def get_by_name(self, name: str) -> Store | None:
        """Retrieve a source website by its unique name."""
        db_source_website = (
            self.db.query(StoreModel).filter(StoreModel.name == name).first()
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
        query = self.db.query(StoreModel)

        # Total count before pagination
        total = query.count()

        # Apply sorting
        if sort_by and hasattr(StoreModel, sort_by):
            order_column = getattr(StoreModel, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        else:
            # Default: most recently created first
            query = query.order_by(desc(StoreModel.created_at))

        # Apply pagination
        source_websites = query.limit(limit).offset(offset).all()

        return [self._to_entity(sw) for sw in source_websites], total

    def update(self, source_website_id: int, source_website: Store) -> Store | None:
        """Update an existing source website."""
        db_source_website = (
            self.db.query(StoreModel).filter(StoreModel.id == source_website_id).first()
        )
        if not db_source_website:
            return None

        try:
            for name in _UPDATABLE:
                setattr(db_source_website, name, getattr(source_website, name))
            setattr(db_source_website, "updated_at", datetime.now(UTC))  # noqa: B010
            self.db.commit()
            self.db.refresh(db_source_website)
            return self._to_entity(db_source_website)
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, source_website_id: int) -> bool:
        """Delete a source website from the database."""
        db_source_website = (
            self.db.query(StoreModel).filter(StoreModel.id == source_website_id).first()
        )
        if not db_source_website:
            return False

        try:
            self.db.delete(db_source_website)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise StoreHasOffersError() from e
        except Exception as e:
            self.db.rollback()
            raise e

    def _to_entity(self, source_website_model: StoreModel) -> Store:
        """Convert StoreModel to Store."""
        return Store(
            **{f.name: getattr(source_website_model, f.name) for f in fields(Store)}
        )
