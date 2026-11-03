from datetime import UTC, datetime

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session, joinedload

from src.app.entities.product import Product as ProductEntity
from src.app.infrastructure.database.models.price_history_model import (
    PriceHistory as PriceHistoryModel,
)
from src.app.infrastructure.database.models.product_model import Product as ProductModel
from src.app.infrastructure.database.text_match import title_contains
from src.app.interfaces.repositories.product_repository import (
    ProductRepositoryInterface,
)


class ProductRepository(ProductRepositoryInterface):
    """SQLAlchemy implementation of ProductRepositoryInterface."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, product: ProductEntity) -> ProductEntity:
        """Create a new product in the database."""
        db_product = ProductModel(**product.model_dump(exclude={"id", "current_price"}))
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return self._to_entity(db_product)

    def _get_latest_price(self, product_id: int) -> float | None:
        """Get the latest price for a product from price_history."""
        result = (
            self.db.query(PriceHistoryModel.price)
            .filter(PriceHistoryModel.product_id == product_id)
            .order_by(desc(PriceHistoryModel.id))
            .first()
        )
        return float(result[0]) if result else None

    def get_by_id(self, product_id: int) -> ProductEntity | None:
        """Retrieve a product by ID with source_website relationship."""
        product = (
            self.db.query(ProductModel)
            .options(joinedload(ProductModel.source_website))
            .filter(ProductModel.id == product_id)
            .first()
        )
        if product:
            entity = self._to_entity(product)
            entity.current_price = self._get_latest_price(product.id)
            return entity
        return None

    def get_by_url(self, url: str) -> ProductEntity | None:
        """Retrieve a product by URL."""
        product = (
            self.db.query(ProductModel)
            .options(joinedload(ProductModel.source_website))
            .filter(ProductModel.url == url)
            .first()
        )
        if product:
            entity = self._to_entity(product)
            entity.current_price = self._get_latest_price(product.id)
            return entity
        return None

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[ProductEntity], int]:
        """Retrieve all products with pagination, sorting and current price."""
        # Subquery: latest price per product
        latest_price_sq = (
            self.db.query(
                PriceHistoryModel.product_id,
                func.max(PriceHistoryModel.id).label("max_id"),
            )
            .group_by(PriceHistoryModel.product_id)
            .subquery()
        )

        price_sq = (
            self.db.query(
                PriceHistoryModel.product_id,
                PriceHistoryModel.price,
            )
            .join(
                latest_price_sq,
                (PriceHistoryModel.product_id == latest_price_sq.c.product_id)
                & (PriceHistoryModel.id == latest_price_sq.c.max_id),
            )
            .subquery()
        )

        query = (
            self.db.query(ProductModel, price_sq.c.price)
            .outerjoin(price_sq, ProductModel.id == price_sq.c.product_id)
            .options(joinedload(ProductModel.source_website))
        )

        # Get total count (count on ProductModel.id to avoid issues with outer join)
        total = (
            self.db.query(func.count(ProductModel.id))
            .select_from(
                ProductModel.__table__.outerjoin(
                    price_sq, ProductModel.id == price_sq.c.product_id
                )
            )
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

        # Apply pagination
        results = query.limit(limit).offset(offset).all()

        entities = []
        for product_model, price in results:
            entity = self._to_entity(product_model)
            entity.current_price = float(price) if price is not None else None
            entities.append(entity)

        return entities, total

    def update(self, product_id: int, product: ProductEntity) -> ProductEntity | None:
        """Update an existing product."""
        db_product = (
            self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
        )
        if not db_product:
            return None

        try:
            for key, value in product.model_dump(
                exclude_unset=True, exclude={"id", "current_price"}
            ).items():
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
        # Subquery: latest price per product
        latest_price_sq = (
            self.db.query(
                PriceHistoryModel.product_id,
                func.max(PriceHistoryModel.id).label("max_id"),
            )
            .group_by(PriceHistoryModel.product_id)
            .subquery()
        )

        price_sq = (
            self.db.query(
                PriceHistoryModel.product_id,
                PriceHistoryModel.price,
            )
            .join(
                latest_price_sq,
                (PriceHistoryModel.product_id == latest_price_sq.c.product_id)
                & (PriceHistoryModel.id == latest_price_sq.c.max_id),
            )
            .subquery()
        )

        # Base query: products matching search_term + source_website_ids
        query = (
            self.db.query(ProductModel, price_sq.c.price)
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

        entities = []
        for product_model, price in results:
            entity = self._to_entity(product_model)
            entity.current_price = float(price) if price is not None else None
            entities.append(entity)

        return entities, total
