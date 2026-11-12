"""POST /offers: collectors send one offer for a book, identified by ISBN.
GET /offers/collection-queue: which books a collector should look up next.

This module is the composition root for offer ingestion: it wires the
database repositories and the BrasilAPI metadata adapter into the use cases.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.app.alerts.persistence.owners import UserAccountOwners
from src.app.alerts.persistence.repositories import (
    NotificationLogRepository,
    PriceAlertRepository,
)
from src.app.alerts.persistence.stores import SourceWebsiteStores
from src.app.alerts.use_cases import EvaluateBookAlertsUseCase, OpportunityNotifier
from src.app.catalog.adapters.brasilapi_books import BrasilApiBookMetadata
from src.app.catalog.http.offer_schema import OfferIngestRequest
from src.app.catalog.http.product_presenter import ProductPresenter
from src.app.catalog.isbn import InvalidIsbnError
from src.app.catalog.persistence.repositories import (
    CanonicalProductRepository,
    PriceHistoryRepository,
    ProductRepository,
)
from src.app.catalog.ports import BookMetadataGateway, BookMetadataUnavailableError
from src.app.catalog.use_cases import (
    BookNotFoundError,
    GetOrCreateBookByIsbnUseCase,
    IngestOfferUseCase,
    InvalidOfferError,
    ListCollectionQueueUseCase,
    OfferInput,
)
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.services.email_service import EmailServiceInterface
from src.app.security.auth import get_current_staff_user
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse
from src.config.logging_config import get_logger

router = APIRouter(tags=["offers"], prefix="/offers")

logger = get_logger(__name__)


def get_book_metadata_gateway() -> BookMetadataGateway:
    """The book metadata source (overridden in tests)."""
    return BrasilApiBookMetadata()


def get_ingest_offer_use_case(
    db=Depends(get_db),
    metadata: BookMetadataGateway = Depends(get_book_metadata_gateway),
) -> IngestOfferUseCase:
    return IngestOfferUseCase(
        get_book=GetOrCreateBookByIsbnUseCase(CanonicalProductRepository(db), metadata),
        offers=ProductRepository(db),
        prices=PriceHistoryRepository(db),
    )


def get_book_alerts_use_case(
    db=Depends(get_db),
    email_service: EmailServiceInterface = Depends(get_email_service),
) -> EvaluateBookAlertsUseCase:
    """Book alerts are checked right after an offer for the book comes in."""
    alerts = PriceAlertRepository(db)
    return EvaluateBookAlertsUseCase(
        product_repo=ProductRepository(db),
        price_alert_repo=alerts,
        source_website_repo=SourceWebsiteStores(SourceWebsiteRepository(db)),
        notifier=OpportunityNotifier(
            NotificationLogRepository(db),
            UserAccountOwners(UserRepository(db)),
            alerts,
            email_service,
        ),
    )


def get_source_website_repository(db=Depends(get_db)) -> SourceWebsiteRepository:
    return SourceWebsiteRepository(db)


def get_collection_queue_use_case(db=Depends(get_db)) -> ListCollectionQueueUseCase:
    return ListCollectionQueueUseCase(CanonicalProductRepository(db))


def _error(status: int, code: str, title: str, detail: str, pointer: str):
    return JSONResponse(
        status_code=status,
        content=JsonApiErrorResponse(
            errors=[
                JsonApiError(
                    status=str(status),
                    code=code,
                    title=title,
                    detail=detail,
                    source={"pointer": pointer},
                )
            ]
        ).model_dump(),
        media_type="application/vnd.api+json",
    )


@router.post("/", status_code=201)
def ingest_offer(
    offer_in: OfferIngestRequest,
    use_case: IngestOfferUseCase = Depends(get_ingest_offer_use_case),
    source_websites: SourceWebsiteRepository = Depends(get_source_website_repository),
    book_alerts: EvaluateBookAlertsUseCase = Depends(get_book_alerts_use_case),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Record one offer for a book. Requires staff access (collectors).

    Finds or creates the book from its ISBN, creates or updates the offer by
    URL, and adds a price-history point. Then checks the book's price alerts
    (a failure there never fails the ingestion).

    Returns:
        - 201: new offer (products resource, with canonical_product_id)
        - 200: existing offer updated
        - 422: invalid ISBN, unknown book, unknown store or invalid values
        - 503: the book metadata source is unavailable
    """
    attrs = offer_in.data.attributes

    if not source_websites.get_by_id(attrs.source_website_id):
        return _error(
            422,
            "UNKNOWN_SOURCE_WEBSITE",
            "Unknown store",
            f"No source website with id {attrs.source_website_id}",
            "/data/attributes/source_website_id",
        )

    try:
        result = use_case.execute(
            OfferInput(
                isbn=attrs.isbn,
                source_website_id=attrs.source_website_id,
                url=attrs.url,
                price=attrs.price,
                condition=attrs.condition,
                is_available=attrs.is_available,
                city=attrs.city,
                state=attrs.state,
            )
        )
    except InvalidIsbnError as exc:
        return _error(
            422, "INVALID_ISBN", "Invalid ISBN", str(exc), "/data/attributes/isbn"
        )
    except BookNotFoundError:
        return _error(
            422,
            "UNKNOWN_ISBN",
            "Unknown book",
            f"No metadata source knows ISBN {attrs.isbn}",
            "/data/attributes/isbn",
        )
    except InvalidOfferError as exc:
        return _error(
            422, "INVALID_OFFER", "Invalid offer", str(exc), "/data/attributes"
        )
    except BookMetadataUnavailableError as exc:
        logger.warning("Book metadata unavailable: %s", exc)
        return _error(
            503,
            "METADATA_UNAVAILABLE",
            "Book metadata source unavailable",
            "Try again later",
            "/data/attributes/isbn",
        )

    logger.info(
        "Offer %s: %s (book %s)",
        "created" if result.created else "updated",
        result.offer.url,
        result.book.id,
        extra={"action": "offer_ingested", "user_id": current_user.id},
    )
    if result.book.id is not None:
        try:
            book_alerts.execute(result.book.id)
        except Exception:  # an alert problem must not lose the price point
            logger.exception("Book alerts failed for book %s", result.book.id)
    body = ProductPresenter.handle_success(result.offer).model_dump(mode="json")
    return JSONResponse(
        status_code=201 if result.created else 200,
        content=body,
        media_type="application/vnd.api+json",
    )


@router.get("/collection-queue")
def collection_queue(
    store: str = Query(description="The store's slug, e.g. estante_virtual"),
    use_case: ListCollectionQueueUseCase = Depends(get_collection_queue_use_case),
    source_websites: SourceWebsiteRepository = Depends(get_source_website_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    The books a collector should look up at a store, stalest first: books the
    store never priced, then the ones whose latest price point is oldest.
    Requires staff access (collectors).

    Returns:
        - 200: collection of collection-queue-items (isbn, last_checked_at)
        - 404: unknown store
    """
    source_website = source_websites.get_by_name(store)
    if not source_website:
        return _error(
            404,
            "UNKNOWN_SOURCE_WEBSITE",
            "Unknown store",
            f"No source website named {store!r}",
            "/store",
        )

    queue = use_case.execute(source_website.id)
    data = [
        {
            "type": "collection-queue-items",
            "id": item.value,
            "attributes": {
                "isbn": item.value,
                "last_checked_at": (
                    item.last_checked_at.isoformat() if item.last_checked_at else None
                ),
            },
        }
        for item in queue
    ]
    return JSONResponse(
        status_code=200,
        content={"data": data, "meta": {"total": len(data)}},
        media_type="application/vnd.api+json",
    )
