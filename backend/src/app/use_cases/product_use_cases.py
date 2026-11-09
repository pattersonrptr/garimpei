from src.app.entities.product import Product as ProductEntity
from src.app.entities.product import ProductListFilters
from src.app.interfaces.repositories.product_repository import (
    ProductRepositoryInterface,
)


class CreateProductUseCase:
    """Use case for creating a new product."""

    def __init__(self, product_repo: ProductRepositoryInterface):
        self.product_repo = product_repo

    def execute(self, product: ProductEntity) -> ProductEntity:
        """
        Create a new product.

        Args:
            product: ProductEntity with product data

        Returns:
            Created ProductEntity with generated ID

        Note:
            Validation should be done before calling this use case
        """
        created_product = self.product_repo.create(product)
        return created_product


class GetProductByIdUseCase:
    """Use case for retrieving a product by ID."""

    def __init__(self, product_repo: ProductRepositoryInterface):
        self.product_repo = product_repo

    def execute(self, product_id: int) -> ProductEntity | None:
        """
        Get a product by its ID.

        Args:
            product_id: The product ID

        Returns:
            ProductEntity if found, None otherwise
        """
        return self.product_repo.get_by_id(product_id)


class GetProductByUrlUseCase:
    """Use case for retrieving a product by URL."""

    def __init__(self, product_repo: ProductRepositoryInterface):
        self.product_repo = product_repo

    def execute(self, url: str) -> ProductEntity | None:
        """
        Get a product by its URL.

        Args:
            url: The product URL

        Returns:
            ProductEntity if found, None otherwise
        """
        return self.product_repo.get_by_url(url)


class ListProductsUseCase:
    """Use case for listing products with pagination."""

    def __init__(self, product_repo: ProductRepositoryInterface):
        self.product_repo = product_repo

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        filters: ProductListFilters | None = None,
    ) -> tuple[list[ProductEntity], int]:
        """
        List products with pagination, sorting and optional filters.

        Args:
            limit: Maximum number of products to return
            offset: Number of products to skip
            sort_by: Field name to sort by
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Tuple of (list of ProductEntity, total count)
        """
        return self.product_repo.get_all(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
        )


class UpdateProductUseCase:
    """Use case for updating an existing product."""

    def __init__(self, product_repo: ProductRepositoryInterface):
        self.product_repo = product_repo

    def execute(
        self,
        product_id: int,
        product_data: ProductEntity,
    ) -> ProductEntity | None:
        """
        Update an existing product.

        Args:
            product_id: The ID of the product to update
            product_data: ProductEntity with updated data

        Returns:
            Updated ProductEntity if product exists, None otherwise
        """
        existing_product = self.product_repo.get_by_id(product_id)
        if not existing_product:
            return None

        # Update fields from product_data
        for key, value in product_data.model_dump(exclude_unset=True).items():
            if key not in ["id", "created_at", "current_price"]:
                setattr(existing_product, key, value)

        updated_product = self.product_repo.update(product_id, existing_product)
        return updated_product


class DeleteProductUseCase:
    """Use case for deleting a product."""

    def __init__(self, product_repo: ProductRepositoryInterface):
        self.product_repo = product_repo

    def execute(self, product_id: int) -> bool:
        """
        Delete a product.

        Args:
            product_id: The ID of the product to delete

        Returns:
            True if successfully deleted, False if not found
        """
        return self.product_repo.delete(product_id)
