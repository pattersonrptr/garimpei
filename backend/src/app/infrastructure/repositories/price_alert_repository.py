from datetime import UTC, datetime

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.app.entities.price_alert import PriceAlert as PriceAlertEntity
from src.app.infrastructure.database.models.price_alert_model import (
    PriceAlert as PriceAlertModel,
)
from src.app.infrastructure.database.models.price_alert_source_website_model import (
    price_alert_source_website,
)
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.interfaces.repositories.price_alert_repository import (
    PriceAlertRepositoryInterface,
)


class PriceAlertRepository(PriceAlertRepositoryInterface):
    """SQLAlchemy implementation of PriceAlertRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: PriceAlertModel) -> PriceAlertEntity:
        """Convert a PriceAlert ORM model to a domain entity."""
        return PriceAlertEntity(
            id=model.id,
            search_term=model.search_term,
            max_price=model.max_price,
            is_active=model.is_active,
            frequency_minutes=model.frequency_minutes,
            last_triggered_at=model.last_triggered_at,
            user_id=model.user_id,
            search_config_id=model.search_config_id,
            source_website_ids=[sw.id for sw in model.source_websites],
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _sync_source_websites(
        self, db_model: PriceAlertModel, source_website_ids: list[int]
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

    def create(self, price_alert: PriceAlertEntity) -> PriceAlertEntity:
        """Persist a new price alert and return it with assigned id."""
        db_price_alert = PriceAlertModel(
            search_term=price_alert.search_term,
            max_price=price_alert.max_price,
            is_active=price_alert.is_active,
            frequency_minutes=price_alert.frequency_minutes,
            last_triggered_at=price_alert.last_triggered_at,
            user_id=price_alert.user_id,
            search_config_id=price_alert.search_config_id,
        )
        self.db.add(db_price_alert)
        self.db.flush()  # get the id before syncing M2M

        self._sync_source_websites(db_price_alert, price_alert.source_website_ids)

        self.db.commit()
        self.db.refresh(db_price_alert)
        return self._to_entity(db_price_alert)

    def get_by_id(self, price_alert_id: int) -> PriceAlertEntity | None:
        """Retrieve a non-deleted price alert by its primary key."""
        db_record = (
            self.db.query(PriceAlertModel)
            .options(joinedload(PriceAlertModel.source_websites))
            .filter(
                PriceAlertModel.id == price_alert_id,
                PriceAlertModel.deleted_at.is_(None),
            )
            .first()
        )
        return self._to_entity(db_record) if db_record else None

    def get_by_user_id(self, user_id: int) -> list[PriceAlertEntity]:
        """Return all non-deleted price alerts for a given user."""
        records = (
            self.db.query(PriceAlertModel)
            .options(joinedload(PriceAlertModel.source_websites))
            .filter(
                PriceAlertModel.user_id == user_id,
                PriceAlertModel.deleted_at.is_(None),
            )
            .all()
        )
        return [self._to_entity(r) for r in records]

    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> PriceAlertEntity | None:
        """Return a non-deleted price alert matching term + user (for uniqueness check)."""
        db_record = (
            self.db.query(PriceAlertModel)
            .filter(
                PriceAlertModel.search_term == search_term,
                PriceAlertModel.user_id == user_id,
                PriceAlertModel.deleted_at.is_(None),
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
    ) -> tuple[list[PriceAlertEntity], int]:
        """Return a paginated list of all price alerts and the total count."""
        query = (
            self.db.query(PriceAlertModel)
            .options(joinedload(PriceAlertModel.source_websites))
            .filter(PriceAlertModel.deleted_at.is_(None))
        )
        if user_id is not None:
            query = query.filter(PriceAlertModel.user_id == user_id)

        total = query.count()

        if sort_by and hasattr(PriceAlertModel, sort_by):
            order_column = getattr(PriceAlertModel, sort_by)
            query = query.order_by(
                desc(order_column) if sort_order == "desc" else asc(order_column)
            )

        records = query.offset(offset).limit(limit).all()
        return [self._to_entity(r) for r in records], total

    def update(
        self, price_alert_id: int, price_alert: PriceAlertEntity
    ) -> PriceAlertEntity | None:
        """Update a price alert. Returns updated entity or None if not found."""
        db_record = (
            self.db.query(PriceAlertModel)
            .options(joinedload(PriceAlertModel.source_websites))
            .filter(PriceAlertModel.id == price_alert_id)
            .first()
        )
        if not db_record:
            return None

        db_record.search_term = price_alert.search_term
        db_record.max_price = price_alert.max_price
        db_record.is_active = price_alert.is_active
        db_record.frequency_minutes = price_alert.frequency_minutes
        db_record.last_triggered_at = price_alert.last_triggered_at
        db_record.user_id = price_alert.user_id
        db_record.search_config_id = price_alert.search_config_id

        self._sync_source_websites(db_record, price_alert.source_website_ids)

        self.db.commit()
        self.db.refresh(db_record)
        return self._to_entity(db_record)

    def delete(self, price_alert_id: int) -> bool:
        """Soft-delete a price alert by setting deleted_at. Returns True if deleted, False if not found."""
        db_record = (
            self.db.query(PriceAlertModel)
            .filter(
                PriceAlertModel.id == price_alert_id,
                PriceAlertModel.deleted_at.is_(None),
            )
            .first()
        )
        if not db_record:
            return False
        db_record.deleted_at = datetime.now(UTC)
        db_record.is_active = False
        self.db.commit()
        return True

    def count_active_by_search_config_id(self, search_config_id: int) -> int:
        """Count active, non-deleted price alerts that reference a given SearchConfig."""
        return (
            self.db.query(PriceAlertModel)
            .filter(
                PriceAlertModel.search_config_id == search_config_id,
                PriceAlertModel.is_active.is_(True),
                PriceAlertModel.deleted_at.is_(None),
            )
            .count()
        )

    def find_matching_alerts_for_product(
        self,
        product_title: str,
        source_website_id: int,
        current_price: float,
    ) -> list[PriceAlertEntity]:
        """Find all active alerts matching a product's title, source and price.

        Matches when:
        - alert.is_active is True
        - alert.search_term appears in product_title (case-insensitive)
        - source_website_id is in alert.source_website_ids (M2M)
        - current_price <= alert.max_price
        """
        # SQL-level filter: active, price fits, source website matches
        records = (
            self.db.query(PriceAlertModel)
            .options(joinedload(PriceAlertModel.source_websites))
            .join(
                price_alert_source_website,
                PriceAlertModel.id == price_alert_source_website.c.price_alert_id,
            )
            .filter(
                PriceAlertModel.is_active.is_(True),
                PriceAlertModel.deleted_at.is_(None),
                PriceAlertModel.max_price >= current_price,
                price_alert_source_website.c.source_website_id == source_website_id,
            )
            .all()
        )
        # Post-filter: search_term must appear in product_title (case-insensitive)
        matched = []
        seen_ids: set[int] = set()
        title_lower = product_title.lower()
        for record in records:
            if record.id in seen_ids:
                continue
            seen_ids.add(record.id)
            if record.search_term.lower() in title_lower:
                matched.append(self._to_entity(record))
        return matched
