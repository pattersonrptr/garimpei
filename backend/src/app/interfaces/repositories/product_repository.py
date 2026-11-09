from abc import ABC, abstractmethod

from src.app.entities.product import Product as ProductEntity
from src.app.entities.product import ProductListFilters


class ProductRepositoryInterface(ABC):
    """
    Interface for Product Repository operations.

    Defines the contract for all product data access operations,
    following the Repository pattern from Domain-Driven Design.
    """

    @abstractmethod
    def create(self, product: ProductEntity) -> ProductEntity:
        """
        Create a new product in the repository.

        Args:
            product: ProductEntity with product data

        Returns:
            ProductEntity: Created product with generated ID

        Raises:
            IntegrityError: If constraints are violated
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, product_id: int) -> ProductEntity | None:
        """
        Retrieve a product by its unique ID.

        Args:
            product_id: The unique identifier of the product

        Returns:
            ProductEntity if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_url(self, url: str) -> ProductEntity | None:
        """
        Retrieve a product by its URL.

        Args:
            url: The product URL

        Returns:
            ProductEntity if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        filters: ProductListFilters | None = None,
    ) -> tuple[list[ProductEntity], int]:
        """
        Retrieve all products with pagination, sorting and optional filters.

        Args:
            limit: Maximum number of products to return
            offset: Number of products to skip
            sort_by: Field name to sort by
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Tuple of (list of ProductEntity, total count)
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, product_id: int, product: ProductEntity) -> ProductEntity | None:
        """
        Update an existing product's information.

        Args:
            product_id: The ID of the product to update
            product: ProductEntity with updated data

        Returns:
            Updated ProductEntity if product exists, None otherwise

        Raises:
            IntegrityError: If update violates constraints
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        """
        Delete a product from the repository.

        Args:
            product_id: The ID of the product to delete

        Returns:
            True if product was deleted, False if product not found
        """
        raise NotImplementedError

    @abstractmethod
    def search_by_term_and_sources(
        self,
        search_term: str,
        source_website_ids: list[int],
        max_price: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list["ProductEntity"], int]:
        """
        Search products whose title matches a search term (case-insensitive)
        and belong to one of the given source websites.

        Optionally filters by max_price (latest price from price_history).
        Results are sorted by latest price ascending.

        Args:
            search_term: Keyword to match against product title
            source_website_ids: List of source website IDs to filter by
            max_price: Optional maximum price filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of ProductEntity with current_price populated, total count)
        """
        raise NotImplementedError
