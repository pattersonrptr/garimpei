from datetime import UTC, datetime

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from src.app.alerts.entities import NotificationLog as NotificationLogEntity
from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.persistence.models import (
    NotificationLog as NotificationLogModel,
)
from src.app.alerts.persistence.models import (
    PriceAlert as PriceAlertModel,
)
from src.app.alerts.persistence.models import (
    price_alert_source_website,
)
from src.app.alerts.ports import (
    NotificationLogRepositoryInterface,
    PriceAlertRepositoryInterface,
)
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database.text_match import text_contains


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

    def count_active_by_user_id(self, user_id: int) -> int:
        """Count active, non-deleted price alerts owned by a user."""
        return (
            self.db.query(PriceAlertModel)
            .filter(
                PriceAlertModel.user_id == user_id,
                PriceAlertModel.is_active.is_(True),
                PriceAlertModel.deleted_at.is_(None),
            )
            .count()
        )

    def count_by_search_config_id(self, search_config_id: int) -> int:
        """Count non-deleted price alerts (active or paused) using a SearchConfig."""
        return (
            self.db.query(PriceAlertModel)
            .filter(
                PriceAlertModel.search_config_id == search_config_id,
                PriceAlertModel.deleted_at.is_(None),
            )
            .count()
        )

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
        - alert.search_term appears in product_title (case/accent-insensitive)
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
        # Post-filter: search_term must appear in product_title
        # (case- and accent-insensitive, same rule as title_contains in SQL)
        matched = []
        seen_ids: set[int] = set()
        for record in records:
            if record.id in seen_ids:
                continue
            seen_ids.add(record.id)
            if text_contains(product_title, record.search_term):
                matched.append(self._to_entity(record))
        return matched


class NotificationLogRepository(NotificationLogRepositoryInterface):
    """SQLAlchemy implementation of NotificationLogRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: NotificationLogModel) -> NotificationLogEntity:
        return NotificationLogEntity(
            id=model.id,
            price_alert_id=model.price_alert_id,
            user_id=model.user_id,
            product_id=model.product_id,
            email_to=model.email_to,
            subject=model.subject,
            status=model.status,
            error_message=model.error_message,
            sent_at=model.sent_at,
            created_at=model.created_at,
        )

    def create(self, notification_log: NotificationLogEntity) -> NotificationLogEntity:
        """Persist a new notification log."""
        db_log = NotificationLogModel(
            price_alert_id=notification_log.price_alert_id,
            user_id=notification_log.user_id,
            product_id=notification_log.product_id,
            email_to=notification_log.email_to,
            subject=notification_log.subject,
            status=notification_log.status,
            error_message=notification_log.error_message,
            sent_at=notification_log.sent_at,
            created_at=notification_log.created_at,
        )
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return self._to_entity(db_log)

    def get_by_id(self, notification_log_id: int) -> NotificationLogEntity | None:
        """Retrieve a notification log by its primary key."""
        db_log = (
            self.db.query(NotificationLogModel)
            .filter(NotificationLogModel.id == notification_log_id)
            .first()
        )
        return self._to_entity(db_log) if db_log else None

    def get_by_price_alert_id(self, price_alert_id: int) -> list[NotificationLogEntity]:
        """Return all logs for a given price alert, ordered by sent_at desc."""
        records = (
            self.db.query(NotificationLogModel)
            .filter(NotificationLogModel.price_alert_id == price_alert_id)
            .order_by(desc(NotificationLogModel.sent_at))
            .all()
        )
        return [self._to_entity(r) for r in records]

    def get_last_sent_for_alert(
        self, price_alert_id: int
    ) -> NotificationLogEntity | None:
        """Return the most recent successfully sent notification for a price alert."""
        db_log = (
            self.db.query(NotificationLogModel)
            .filter(
                NotificationLogModel.price_alert_id == price_alert_id,
                NotificationLogModel.status == "sent",
            )
            .order_by(desc(NotificationLogModel.sent_at))
            .first()
        )
        return self._to_entity(db_log) if db_log else None

    def count_since(self, price_alert_id: int, since: datetime) -> int:
        """Count successfully sent notifications for a price alert since a given time."""
        return (
            self.db.query(NotificationLogModel)
            .filter(
                NotificationLogModel.price_alert_id == price_alert_id,
                NotificationLogModel.status == "sent",
                NotificationLogModel.sent_at >= since,
            )
            .count()
        )

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[NotificationLogEntity], int]:
        """Return a paginated list of all notification logs and the total count."""
        query = self.db.query(NotificationLogModel)

        total = query.count()

        if sort_by and hasattr(NotificationLogModel, sort_by):
            order_column = getattr(NotificationLogModel, sort_by)
            query = query.order_by(
                desc(order_column) if sort_order == "desc" else asc(order_column)
            )
        else:
            query = query.order_by(desc(NotificationLogModel.sent_at))

        records = query.limit(limit).offset(offset).all()
        return [self._to_entity(r) for r in records], total

    def delete(self, notification_log_id: int) -> bool:
        """Delete a notification log by id."""
        db_log = (
            self.db.query(NotificationLogModel)
            .filter(NotificationLogModel.id == notification_log_id)
            .first()
        )
        if not db_log:
            return False
        self.db.delete(db_log)
        self.db.commit()
        return True

    def exists_for_alert_and_product(
        self, price_alert_id: int, product_id: int
    ) -> bool:
        """Check if a successful notification was already sent for alert + product."""
        return (
            self.db.query(NotificationLogModel)
            .filter(
                NotificationLogModel.price_alert_id == price_alert_id,
                NotificationLogModel.product_id == product_id,
                NotificationLogModel.status == "sent",
            )
            .count()
            > 0
        )
