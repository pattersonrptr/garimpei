from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import and_, asc, desc, exists, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.app.alerts.persistence.models import (
    NotificationLog as NotificationLogModel,
)
from src.app.alerts.persistence.models import (
    PriceAlert as PriceAlertModel,
)
from src.app.alerts.persistence.models import (
    price_alert_source_website,
)
from src.app.catalog.entities import CanonicalProduct as CanonicalProductEntity
from src.app.catalog.entities import (
    IdentifierKind,
    ProductCondition,
    ProductListFilters,
    QueuedProduct,
)
from src.app.catalog.entities import PriceHistory as PriceHistoryEntity
from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.entities import ProductIdentifier as ProductIdentifierEntity
from src.app.catalog.persistence.models import (
    CanonicalProduct as CanonicalProductModel,
)
from src.app.catalog.persistence.models import (
    PriceHistory as PriceHistoryModel,
)
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.models import (
    ProductIdentifier as ProductIdentifierModel,
)
from src.app.catalog.ports import (
    CanonicalProductRepositoryInterface,
    CollectionQueueRepositoryInterface,
    PriceHistoryRepositoryInterface,
    ProductRepositoryInterface,
)
from src.app.infrastructure.database.text_match import title_contains


def _as_utc(moment: datetime | None) -> datetime | None:
    """Timestamps are stored as naive UTC; give them their zone back so an API
    client can tell how long ago they were."""
    if moment is None or moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=UTC)


def _persisted_fields(product: ProductEntity) -> dict:
    """The entity's columns as a dict (``id`` and the latest price point's
    ``current_price`` and ``last_checked_at`` are not stored)."""
    data = asdict(product)
    data.pop("id")
    data.pop("current_price")
    data.pop("last_checked_at")
    return data


class ProductRepository(ProductRepositoryInterface):
    """SQLAlchemy implementation of ProductRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, product: ProductEntity) -> ProductEntity:
        """Create a new product in the database."""
        db_product = ProductModel(**_persisted_fields(product))
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return self._to_entity(db_product)

    def _with_latest_price(self, product: ProductModel) -> ProductEntity:
        """The entity with its latest price point (price and when it was seen)."""
        entity = self._to_entity(product)
        point = (
            self.db.query(PriceHistoryModel.price, PriceHistoryModel.created_at)
            .filter(PriceHistoryModel.product_id == product.id)
            .order_by(desc(PriceHistoryModel.id))
            .first()
        )
        if point:
            entity.current_price = float(point.price)
            entity.last_checked_at = _as_utc(point.created_at)
        return entity

    def _latest_price_subquery(self):
        """product_id, price, created_at of each product's latest price point."""
        latest = (
            self.db.query(
                PriceHistoryModel.product_id,
                func.max(PriceHistoryModel.id).label("max_id"),
            )
            .group_by(PriceHistoryModel.product_id)
            .subquery()
        )
        return (
            self.db.query(
                PriceHistoryModel.product_id,
                PriceHistoryModel.price,
                PriceHistoryModel.created_at,
            )
            .join(
                latest,
                (PriceHistoryModel.product_id == latest.c.product_id)
                & (PriceHistoryModel.id == latest.c.max_id),
            )
            .subquery()
        )

    def _rows_to_entities(self, rows) -> list[ProductEntity]:
        entities = []
        for product_model, price, checked_at in rows:
            entity = self._to_entity(product_model)
            entity.current_price = float(price) if price is not None else None
            entity.last_checked_at = _as_utc(checked_at)
            entities.append(entity)
        return entities

    def get_by_id(self, product_id: int) -> ProductEntity | None:
        """Retrieve a product by ID with source_website relationship."""
        product = (
            self.db.query(ProductModel)
            .options(joinedload(ProductModel.source_website))
            .filter(ProductModel.id == product_id)
            .first()
        )
        return self._with_latest_price(product) if product else None

    def get_by_url(self, url: str) -> ProductEntity | None:
        """Retrieve a product by URL."""
        product = (
            self.db.query(ProductModel)
            .options(joinedload(ProductModel.source_website))
            .filter(ProductModel.url == url)
            .first()
        )
        return self._with_latest_price(product) if product else None

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        filters: ProductListFilters | None = None,
    ) -> tuple[list[ProductEntity], int]:
        """Retrieve products with pagination, sorting, filters and current price."""
        price_sq = self._latest_price_subquery()

        conditions = self._filter_conditions(filters, price_sq.c.price)

        query = (
            self.db.query(ProductModel, price_sq.c.price, price_sq.c.created_at)
            .outerjoin(price_sq, ProductModel.id == price_sq.c.product_id)
            .options(joinedload(ProductModel.source_website))
            .filter(*conditions)
        )

        # Get total count (count on ProductModel.id to avoid issues with outer join)
        total = (
            self.db.query(func.count(ProductModel.id))
            .select_from(ProductModel)
            .outerjoin(price_sq, ProductModel.id == price_sq.c.product_id)
            .filter(*conditions)
            .scalar()
        )

        # Apply sorting
        if sort_by and hasattr(ProductModel, sort_by):
            order_column = getattr(ProductModel, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
        else:
            # Default sorting by created_at desc
            query = query.order_by(desc(ProductModel.created_at))
        query = query.order_by(desc(ProductModel.id))  # stable pages

        # Apply pagination
        results = query.limit(limit).offset(offset).all()

        return self._rows_to_entities(results), total

    @staticmethod
    def _filter_conditions(filters: ProductListFilters | None, current_price) -> list:
        """SQL conditions for a ProductListFilters (see its docstring)."""
        if filters is None:
            return []
        conditions = []
        if filters.title:
            conditions.append(title_contains(ProductModel.title, filters.title))
        if filters.condition:
            conditions.append(
                ProductModel.condition == ProductCondition(filters.condition.lower())
            )
        if filters.is_available is not None:
            conditions.append(ProductModel.is_available.is_(filters.is_available))
        if filters.source_website_id is not None:
            conditions.append(
                ProductModel.source_website_id == filters.source_website_id
            )
        if (
            filters.matching_user_id is not None
            or filters.matching_alert_id is not None
        ):
            alert_matches = [
                PriceAlertModel.deleted_at.is_(None),
                price_alert_source_website.c.price_alert_id == PriceAlertModel.id,
                price_alert_source_website.c.source_website_id
                == ProductModel.source_website_id,
                title_contains(ProductModel.title, PriceAlertModel.search_term),
            ]
            if filters.matching_user_id is not None:
                alert_matches.append(
                    PriceAlertModel.user_id == filters.matching_user_id
                )
            if filters.matching_alert_id is not None:
                alert_matches.append(PriceAlertModel.id == filters.matching_alert_id)
            if filters.opportunities_only:
                alert_matches.append(current_price <= PriceAlertModel.max_price)
            conditions.append(
                exists()
                .where(and_(*alert_matches))
                .correlate_except(PriceAlertModel, price_alert_source_website)
            )
        return conditions

    def update(self, product_id: int, product: ProductEntity) -> ProductEntity | None:
        """Update an existing product."""
        db_product = (
            self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
        )
        if not db_product:
            return None

        try:
            for key, value in _persisted_fields(product).items():
                setattr(db_product, key, value)

            db_product.updated_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(db_product)
            return self._to_entity(db_product)
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, product_id: int) -> bool:
        """Delete a product from the database."""
        db_product = (
            self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
        )
        if not db_product:
            return False

        try:
            # Sent notifications are history: keep them, without the product.
            self.db.query(NotificationLogModel).filter(
                NotificationLogModel.product_id == product_id
            ).update({NotificationLogModel.product_id: None}, synchronize_session=False)
            self.db.delete(db_product)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def _to_entity(self, product_model: ProductModel) -> ProductEntity:
        """
        Convert ProductModel to ProductEntity.

        Calculates current_price from price_history relationship when available.
        """
        product_dict = {
            "id": product_model.id,
            "url": product_model.url,
            "title": product_model.title,
            "source_product_code": product_model.source_product_code,
            "description": product_model.description,
            "image_urls": product_model.image_urls,
            "city": product_model.city,
            "state": product_model.state,
            "condition": product_model.condition,
            "seller_name": product_model.seller_name,
            "is_available": product_model.is_available,
            "source_website_id": product_model.source_website_id,
            "source_metadata": product_model.source_metadata,
            "canonical_product_id": product_model.canonical_product_id,
            "created_at": product_model.created_at,
            "updated_at": product_model.updated_at,
            "current_price": None,  # Will be populated from price_history later
        }
        return ProductEntity(**product_dict)

    def search_by_term_and_sources(
        self,
        search_term: str,
        source_website_ids: list[int],
        max_price: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProductEntity], int]:
        """Search products by title (case/accent-insensitive) + source_website_ids, with latest price."""
        price_sq = self._latest_price_subquery()

        # Base query: products matching search_term + source_website_ids
        query = (
            self.db.query(ProductModel, price_sq.c.price, price_sq.c.created_at)
            .outerjoin(price_sq, ProductModel.id == price_sq.c.product_id)
            .filter(
                title_contains(ProductModel.title, search_term),
                ProductModel.source_website_id.in_(source_website_ids),
                ProductModel.is_available.is_(True),
            )
        )

        # Optional max_price filter
        if max_price is not None:
            query = query.filter(price_sq.c.price <= max_price)

        total = query.count()

        # Sort by price ascending (cheapest first), nulls last
        query = query.order_by(
            asc(price_sq.c.price).nulls_last(),
            desc(ProductModel.updated_at),
        )

        results = query.offset(offset).limit(limit).all()

        return self._rows_to_entities(results), total


class PriceHistoryRepository(PriceHistoryRepositoryInterface):
    """SQLAlchemy implementation of PriceHistoryRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def _to_entity(self, model: PriceHistoryModel) -> PriceHistoryEntity:
        return PriceHistoryEntity(
            id=model.id,
            product_id=model.product_id,
            price=float(model.price),
            created_at=_as_utc(model.created_at),
        )

    def create(self, price_history: PriceHistoryEntity) -> PriceHistoryEntity:
        """Persist a new price record."""
        db_price_history = PriceHistoryModel(
            product_id=price_history.product_id,
            price=price_history.price,
        )
        self.db.add(db_price_history)
        self.db.commit()
        self.db.refresh(db_price_history)
        return self._to_entity(db_price_history)

    def get_by_id(self, price_history_id: int) -> PriceHistoryEntity | None:
        """Retrieve a price record by its primary key."""
        db_record = (
            self.db.query(PriceHistoryModel)
            .filter(PriceHistoryModel.id == price_history_id)
            .first()
        )
        return self._to_entity(db_record) if db_record else None

    def get_by_product_id(self, product_id: int) -> list[PriceHistoryEntity]:
        """Return all price records for a product, ordered by created_at desc."""
        records = (
            self.db.query(PriceHistoryModel)
            .filter(PriceHistoryModel.product_id == product_id)
            .order_by(desc(PriceHistoryModel.created_at))
            .all()
        )
        return [self._to_entity(r) for r in records]

    def get_latest_by_product_id(self, product_id: int) -> PriceHistoryEntity | None:
        """Return the most recent price record for a product."""
        db_record = (
            self.db.query(PriceHistoryModel)
            .filter(PriceHistoryModel.product_id == product_id)
            .order_by(desc(PriceHistoryModel.created_at))
            .first()
        )
        return self._to_entity(db_record) if db_record else None

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[PriceHistoryEntity], int]:
        """Return a paginated list of all price records and the total count."""
        query = self.db.query(PriceHistoryModel)

        total = query.count()

        if sort_by and hasattr(PriceHistoryModel, sort_by):
            order_column = getattr(PriceHistoryModel, sort_by)
            query = query.order_by(
                desc(order_column) if sort_order == "desc" else asc(order_column)
            )
        else:
            query = query.order_by(desc(PriceHistoryModel.created_at))

        records = query.limit(limit).offset(offset).all()
        return [self._to_entity(r) for r in records], total

    def delete(self, price_history_id: int) -> bool:
        """Delete a price record by id."""
        db_record = (
            self.db.query(PriceHistoryModel)
            .filter(PriceHistoryModel.id == price_history_id)
            .first()
        )
        if not db_record:
            return False
        self.db.delete(db_record)
        self.db.commit()
        return True


class CanonicalProductRepository(
    CanonicalProductRepositoryInterface, CollectionQueueRepositoryInterface
):
    """SQLAlchemy implementation of the canonical product ports."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_identifier(
        self, kind: IdentifierKind, value: str
    ) -> CanonicalProductEntity | None:
        row = (
            self.db.query(CanonicalProductModel)
            .join(ProductIdentifierModel)
            .filter(
                ProductIdentifierModel.kind == IdentifierKind(kind).value,
                ProductIdentifierModel.value == value,
            )
            .first()
        )
        return self._to_entity(row) if row else None

    def create(self, product: CanonicalProductEntity) -> CanonicalProductEntity:
        row = CanonicalProductModel(
            category=product.category.value,
            title=product.title,
            attributes=product.attributes,
            identifiers=[
                ProductIdentifierModel(kind=i.kind.value, value=i.value)
                for i in product.identifiers
            ],
        )
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError:
            # Another request stored the same identifier first: reuse its product.
            self.db.rollback()
            for identifier in product.identifiers:
                existing = self.get_by_identifier(identifier.kind, identifier.value)
                if existing:
                    return existing
            raise
        self.db.refresh(row)
        return self._to_entity(row)

    def list_by_staleness(
        self, kind: IdentifierKind, source_website_id: int
    ) -> list[QueuedProduct]:
        last_point = (
            self.db.query(
                ProductModel.canonical_product_id.label("canonical_product_id"),
                func.max(PriceHistoryModel.created_at).label("last_checked_at"),
            )
            .join(PriceHistoryModel, PriceHistoryModel.product_id == ProductModel.id)
            .filter(
                ProductModel.source_website_id == source_website_id,
                ProductModel.canonical_product_id.isnot(None),
            )
            .group_by(ProductModel.canonical_product_id)
            .subquery()
        )
        rows = (
            self.db.query(ProductIdentifierModel.value, last_point.c.last_checked_at)
            .outerjoin(
                last_point,
                last_point.c.canonical_product_id
                == ProductIdentifierModel.canonical_product_id,
            )
            .filter(ProductIdentifierModel.kind == IdentifierKind(kind).value)
            # "IS NULL DESC" puts never-priced products first on SQLite and
            # Postgres alike (their default NULL ordering differs).
            .order_by(
                last_point.c.last_checked_at.is_(None).desc(),
                last_point.c.last_checked_at.asc(),
                ProductIdentifierModel.value,
            )
            .all()
        )
        return [
            QueuedProduct(kind=kind, value=value, last_checked_at=_as_utc(last))
            for value, last in rows
        ]

    @staticmethod
    def _to_entity(row: CanonicalProductModel) -> CanonicalProductEntity:
        return CanonicalProductEntity(
            id=row.id,
            category=row.category,
            title=row.title,
            attributes=dict(row.attributes or {}),
            identifiers=[
                ProductIdentifierEntity(id=i.id, kind=i.kind, value=i.value)
                for i in row.identifiers
            ],
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
