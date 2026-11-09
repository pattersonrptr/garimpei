from abc import ABC, abstractmethod

from src.app.catalog.entities import (
    BookMetadata,
    CanonicalProduct,
    IdentifierKind,
    ProductListFilters,
)
from src.app.catalog.entities import PriceHistory as PriceHistoryEntity
from src.app.catalog.entities import Product as ProductEntity


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


class PriceHistoryRepositoryInterface(ABC):
    """Abstract interface for PriceHistory data access."""

    @abstractmethod
    def create(self, price_history: PriceHistoryEntity) -> PriceHistoryEntity:
        """Persist a new price record and return it with assigned id."""
        ...

    @abstractmethod
    def get_by_id(self, price_history_id: int) -> PriceHistoryEntity | None:
        """Retrieve a price record by its primary key."""
        ...

    @abstractmethod
    def get_by_product_id(self, product_id: int) -> list[PriceHistoryEntity]:
        """Return all price records for a given product, ordered by created_at desc."""
        ...

    @abstractmethod
    def get_latest_by_product_id(self, product_id: int) -> PriceHistoryEntity | None:
        """Return the most recent price record for a given product."""
        ...

    @abstractmethod
    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[PriceHistoryEntity], int]:
        """Return a paginated list of all price records and the total count."""
        ...

    @abstractmethod
    def delete(self, price_history_id: int) -> bool:
        """Delete a price record by id. Returns True if deleted, False if not found."""
        ...


class BookMetadataUnavailableError(Exception):
    """The metadata source could not answer (network, timeout, server error)."""


class BookMetadataGateway(ABC):
    """What the catalog needs from a book metadata source.

    BrasilAPI, another provider or a test double all plug in here.
    """

    @abstractmethod
    def fetch(self, isbn13: str) -> BookMetadata | None:
        """Metadata for the ISBN-13, or None if the source does not know it.

        Raises:
            BookMetadataUnavailableError: the source could not be reached or failed.
        """
        raise NotImplementedError


class CanonicalProductRepositoryInterface(ABC):
    """Storage the catalog needs for canonical products."""

    @abstractmethod
    def get_by_identifier(
        self, kind: IdentifierKind, value: str
    ) -> CanonicalProduct | None:
        """The canonical product that has this identifier, if any."""
        raise NotImplementedError

    @abstractmethod
    def create(self, product: CanonicalProduct) -> CanonicalProduct:
        """Store a new canonical product with its identifiers.

        If another request created a product with the same identifier first,
        returns that one instead of failing.
        """
        raise NotImplementedError
