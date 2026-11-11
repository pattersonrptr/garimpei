from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, fields

from src.app.catalog.entities import (
    BookMetadata,
    CanonicalProduct,
    IdentifierKind,
    ProductCategory,
    ProductCondition,
    ProductListFilters,
    QueuedProduct,
)
from src.app.catalog.entities import PriceHistory as PriceHistoryEntity
from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.isbn import InvalidIsbnError, normalize_isbn
from src.app.catalog.matching import IsbnMatcher
from src.app.catalog.ports import (
    BookMetadataGateway,
    BookMetadataUnavailableError,
    CanonicalProductRepositoryInterface,
    CollectionQueueRepositoryInterface,
    PriceHistoryRepositoryInterface,
    ProductRepositoryInterface,
)

# An update never touches these: the id and creation time identify the product,
# the current price and last check come from price history, and updated_at is
# set on save.
_PROTECTED_PRODUCT_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "current_price",
    "last_checked_at",
}


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
        for data_field in fields(product_data):
            if data_field.name not in _PROTECTED_PRODUCT_FIELDS:
                setattr(
                    existing_product,
                    data_field.name,
                    getattr(product_data, data_field.name),
                )

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


class CreatePriceHistoryUseCase:
    """Record a new price entry for a product."""

    def __init__(self, price_history_repo: PriceHistoryRepositoryInterface):
        self.price_history_repo = price_history_repo

    def execute(self, price_history: PriceHistoryEntity) -> PriceHistoryEntity:
        return self.price_history_repo.create(price_history)


class GetPriceHistoryByIdUseCase:
    """Retrieve a single price record by its id."""

    def __init__(self, price_history_repo: PriceHistoryRepositoryInterface):
        self.price_history_repo = price_history_repo

    def execute(self, price_history_id: int) -> PriceHistoryEntity | None:
        return self.price_history_repo.get_by_id(price_history_id)


class GetPriceHistoryByProductIdUseCase:
    """Retrieve all price records for a given product."""

    def __init__(self, price_history_repo: PriceHistoryRepositoryInterface):
        self.price_history_repo = price_history_repo

    def execute(self, product_id: int) -> list[PriceHistoryEntity]:
        return self.price_history_repo.get_by_product_id(product_id)


class GetLatestPriceByProductIdUseCase:
    """Retrieve the most recent price record for a given product."""

    def __init__(self, price_history_repo: PriceHistoryRepositoryInterface):
        self.price_history_repo = price_history_repo

    def execute(self, product_id: int) -> PriceHistoryEntity | None:
        return self.price_history_repo.get_latest_by_product_id(product_id)


class ListPriceHistoriesUseCase:
    """List all price records with pagination and sorting."""

    def __init__(self, price_history_repo: PriceHistoryRepositoryInterface):
        self.price_history_repo = price_history_repo

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[PriceHistoryEntity], int]:
        return self.price_history_repo.get_all(
            limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
        )


class DeletePriceHistoryUseCase:
    """Delete a price record by id."""

    def __init__(self, price_history_repo: PriceHistoryRepositoryInterface):
        self.price_history_repo = price_history_repo

    def execute(self, price_history_id: int) -> bool:
        return self.price_history_repo.delete(price_history_id)


class BookNotFoundError(Exception):
    """The ISBN is valid but no metadata source knows the book."""


def _book_attributes(book: BookMetadata) -> dict:
    """The category-specific attributes of a book, without empty values."""
    attributes = {
        "subtitle": book.subtitle,
        "authors": list(book.authors),
        "publisher": book.publisher,
        "year": book.year,
        "page_count": book.page_count,
        "synopsis": book.synopsis,
        "cover_url": book.cover_url,
    }
    return {key: value for key, value in attributes.items() if value}


class GetOrCreateBookByIsbnUseCase:
    """Find the book with this ISBN, creating it from its metadata if new."""

    def __init__(
        self,
        products: CanonicalProductRepositoryInterface,
        metadata: BookMetadataGateway,
        matcher: IsbnMatcher | None = None,
    ):
        self.products = products
        self.metadata = metadata
        self.matcher = matcher or IsbnMatcher()

    def execute(self, isbn: str) -> CanonicalProduct:
        """
        Args:
            isbn: ISBN-10 or ISBN-13, with or without hyphens

        Returns:
            The existing or newly created book

        Raises:
            InvalidIsbnError: ``isbn`` is not a valid ISBN
            BookNotFoundError: no metadata source knows the book
            BookMetadataUnavailableError: the metadata source failed
        """
        identifier = self.matcher.identify(isbn)
        if identifier is None:
            raise InvalidIsbnError(f"Not a valid ISBN: {isbn!r}")

        existing = self.products.get_by_identifier(identifier.kind, identifier.value)
        if existing:
            return existing

        book = self.metadata.fetch(identifier.value)
        if book is None:
            raise BookNotFoundError(identifier.value)

        return self.products.create(
            CanonicalProduct(
                category=ProductCategory.BOOK,
                title=book.title,
                attributes=_book_attributes(book),
                identifiers=[identifier],
            )
        )


class ListCollectionQueueUseCase:
    """The books a collector should look up at one store, stalest first.

    A daily run walks the list in order, so a run cut short (the PC turned off,
    the store blocked) leaves the freshest books for last, and the next run
    starts where the gaps are.
    """

    def __init__(self, products: CollectionQueueRepositoryInterface):
        self.products = products

    def execute(self, source_website_id: int) -> list[QueuedProduct]:
        return self.products.list_by_staleness(IdentifierKind.ISBN13, source_website_id)


class InvalidOfferError(ValueError):
    """The offer sent by a collector is missing data or has impossible values."""


@dataclass(frozen=True, kw_only=True)
class OfferInput:
    """One offer as a collector sees it: a plain DTO, no database ids but the store's.

    Only what the scraping rule allows: price, link, condition, availability,
    store and seller city. The book's title and authors come from its metadata.
    """

    isbn: str
    source_website_id: int
    url: str
    price: float
    condition: ProductCondition
    is_available: bool = True
    city: str | None = None
    state: str | None = None


@dataclass(frozen=True, kw_only=True)
class IngestOfferResult:
    offer: ProductEntity
    book: CanonicalProduct
    created: bool


# products.title is String(255); a canonical title can be longer.
_OFFER_TITLE_MAX = 255


class IngestOfferUseCase:
    """Record one offer for a book: find or create the book, upsert the offer by
    URL, and add a price-history point.

    Every call adds a point, so a collector that checks once a day builds one
    point per offer per day.
    """

    def __init__(
        self,
        get_book: GetOrCreateBookByIsbnUseCase,
        offers: ProductRepositoryInterface,
        prices: PriceHistoryRepositoryInterface,
    ):
        self.get_book = get_book
        self.offers = offers
        self.prices = prices

    def execute(self, offer_in: OfferInput) -> IngestOfferResult:
        """
        Raises:
            InvalidOfferError: empty URL or a price that is not positive
            InvalidIsbnError, BookNotFoundError, BookMetadataUnavailableError:
                see GetOrCreateBookByIsbnUseCase
        """
        url = offer_in.url.strip()
        if not url:
            raise InvalidOfferError("The offer has no URL")
        if offer_in.price <= 0:
            raise InvalidOfferError(f"Price must be positive, got {offer_in.price}")

        book = self.get_book.execute(offer_in.isbn)
        title = book.title[:_OFFER_TITLE_MAX]

        existing = self.offers.get_by_url(url)
        if existing:
            existing.title = title
            existing.condition = ProductCondition(offer_in.condition)
            existing.is_available = offer_in.is_available
            existing.city = offer_in.city
            existing.state = offer_in.state
            existing.canonical_product_id = book.id
            offer = self.offers.update(existing.id, existing) or existing
            created = False
        else:
            offer = self.offers.create(
                ProductEntity(
                    url=url,
                    title=title,
                    source_website_id=offer_in.source_website_id,
                    condition=offer_in.condition,
                    is_available=offer_in.is_available,
                    city=offer_in.city,
                    state=offer_in.state,
                    canonical_product_id=book.id,
                )
            )
            created = True

        point = self.prices.create(
            PriceHistoryEntity(product_id=offer.id, price=offer_in.price)
        )
        offer.current_price = offer_in.price
        offer.last_checked_at = point.created_at
        return IngestOfferResult(offer=offer, book=book, created=created)


@dataclass
class SeedLoadReport:
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


class LoadSeedBooksUseCase:
    """Make sure every ISBN of a seed list is a book in the catalog.

    Idempotent: books already there are left alone and cost no outside call.
    One bad ISBN does not stop the rest; it is reported.
    """

    def __init__(
        self,
        get_book: GetOrCreateBookByIsbnUseCase,
        products: CanonicalProductRepositoryInterface,
        pause: Callable[[], None] = lambda: None,
    ):
        self.get_book = get_book
        self.products = products
        self.pause = pause  # between outside lookups, to be gentle with the source

    def execute(self, isbns: Iterable[str]) -> SeedLoadReport:
        report = SeedLoadReport()
        for raw in isbns:
            try:
                isbn13 = normalize_isbn(raw)
            except InvalidIsbnError:
                report.failed.append((raw, "invalid ISBN"))
                continue
            if self.products.get_by_identifier(IdentifierKind.ISBN13, isbn13):
                report.existing.append(isbn13)
                continue
            try:
                self.get_book.execute(isbn13)
                report.created.append(isbn13)
            except BookNotFoundError:
                report.failed.append((isbn13, "unknown to the metadata source"))
            except BookMetadataUnavailableError as exc:
                report.failed.append((isbn13, f"metadata source unavailable: {exc}"))
            self.pause()
        return report
