from src.app.alerts.ports import (
    BookFinder,
    PriceAlertRepositoryInterface,
    StoreReader,
)
from src.common.jsonapi import JsonApiError


class PriceAlertValidator:
    """Validates price alert create and update requests."""

    def __init__(
        self,
        price_alert_repo: PriceAlertRepositoryInterface,
        source_website_repo: StoreReader,
        book_finder: BookFinder | None = None,
    ):
        self.price_alert_repo = price_alert_repo
        self.source_website_repo = source_website_repo
        self.book_finder = book_finder

    def validate_create_request(self, price_alert_in) -> list[JsonApiError]:
        """
        Validates a price alert creation request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "price_alert"
        if price_alert_in.data.type != "price_alert":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'price_alert', got '{price_alert_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = price_alert_in.data.attributes

        # Validation 2: a keyword (search_term) or a book (isbn), not both
        if attrs.isbn is not None:
            if attrs.search_term:
                errors.append(
                    JsonApiError(
                        status="422",
                        code="INVALID_FIELD",
                        title="Validation error",
                        detail="Send either 'search_term' or 'isbn', not both",
                        source={"pointer": "/data/attributes/isbn"},
                    )
                )
        elif not attrs.search_term or not attrs.search_term.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'search_term' is required",
                    source={"pointer": "/data/attributes/search_term"},
                )
            )

        # Validation 3: user_id required
        if attrs.user_id is None:
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'user_id' is required",
                    source={"pointer": "/data/attributes/user_id"},
                )
            )

        # Validation 4: max_price must be positive
        if attrs.max_price is not None and attrs.max_price <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'max_price' must be a positive number",
                    source={"pointer": "/data/attributes/max_price"},
                )
            )

        # Validation 5: frequency_minutes must be positive if provided
        if attrs.frequency_minutes is not None and attrs.frequency_minutes <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'frequency_minutes' must be a positive integer",
                    source={"pointer": "/data/attributes/frequency_minutes"},
                )
            )

        # Return early if field-level errors
        if errors:
            return errors

        # Validation 6: each source_website_id must exist
        for sw_id in attrs.source_website_ids or []:
            existing_sw = self.source_website_repo.get_by_id(sw_id)
            if not existing_sw:
                errors.append(
                    JsonApiError(
                        status="404",
                        code="SOURCE_WEBSITE_NOT_FOUND",
                        title="Related resource not found",
                        detail=f"SourceWebsite with id '{sw_id}' does not exist",
                        source={"pointer": "/data/attributes/source_website_ids"},
                    )
                )

        if errors:
            return errors

        if attrs.isbn is not None:
            return self._validate_book_alert(attrs)

        # Validation 7: search_term must be unique per user_id
        existing = self.price_alert_repo.get_by_search_term_and_user_id(
            attrs.search_term, attrs.user_id
        )
        if existing:
            errors.append(
                JsonApiError(
                    status="409",
                    code="DUPLICATE_SEARCH_TERM",
                    title="Conflict",
                    detail=f"A price alert with term '{attrs.search_term}' already exists for this user",
                    source={"pointer": "/data/attributes/search_term"},
                )
            )

        return errors

    def _validate_book_alert(self, attrs) -> list[JsonApiError]:
        """The book must be in the catalog; one alert per user, book and condition."""
        book = self.book_finder.find_by_isbn(attrs.isbn) if self.book_finder else None
        if book is None:
            return [
                JsonApiError(
                    status="404",
                    code="BOOK_NOT_FOUND",
                    title="Related resource not found",
                    detail=f"No book with ISBN '{attrs.isbn}' in the catalog",
                    source={"pointer": "/data/attributes/isbn"},
                )
            ]
        existing = self.price_alert_repo.get_by_book_and_user_id(
            book.id, attrs.user_id, attrs.condition or "any"
        )
        if existing:
            return [
                JsonApiError(
                    status="409",
                    code="DUPLICATE_BOOK_ALERT",
                    title="Conflict",
                    detail="This user already has an alert on this book and condition",
                    source={"pointer": "/data/attributes/isbn"},
                )
            ]
        return []

    def validate_update_request(
        self, price_alert_id: int, price_alert_in
    ) -> list[JsonApiError]:
        """
        Validates a price alert update request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "price_alert"
        if price_alert_in.data.type != "price_alert":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'price_alert', got '{price_alert_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = price_alert_in.data.attributes

        # Validation 2: search_term cannot be empty if provided
        if attrs.search_term is not None and not attrs.search_term.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_VALUE",
                    title="Validation error",
                    detail="Field 'search_term' cannot be empty",
                    source={"pointer": "/data/attributes/search_term"},
                )
            )

        # Validation 3: max_price must be positive if provided
        if attrs.max_price is not None and attrs.max_price <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'max_price' must be a positive number",
                    source={"pointer": "/data/attributes/max_price"},
                )
            )

        # Validation 4: frequency_minutes must be positive if provided
        if attrs.frequency_minutes is not None and attrs.frequency_minutes <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'frequency_minutes' must be a positive integer",
                    source={"pointer": "/data/attributes/frequency_minutes"},
                )
            )

        # Return early if field-level errors
        if errors:
            return errors

        # Validation 5: each source_website_id must exist
        for sw_id in attrs.source_website_ids or []:
            existing_sw = self.source_website_repo.get_by_id(sw_id)
            if not existing_sw:
                errors.append(
                    JsonApiError(
                        status="404",
                        code="SOURCE_WEBSITE_NOT_FOUND",
                        title="Related resource not found",
                        detail=f"SourceWebsite with id '{sw_id}' does not exist",
                        source={"pointer": "/data/attributes/source_website_ids"},
                    )
                )

        if errors:
            return errors

        # Validation 6: search_term uniqueness per user (only when search_term is being updated)
        if attrs.search_term is not None:
            existing_alert = self.price_alert_repo.get_by_id(price_alert_id)
            if existing_alert:
                user_id = existing_alert.user_id
                duplicate = self.price_alert_repo.get_by_search_term_and_user_id(
                    attrs.search_term, user_id
                )
                if duplicate and duplicate.id != price_alert_id:
                    errors.append(
                        JsonApiError(
                            status="409",
                            code="DUPLICATE_SEARCH_TERM",
                            title="Conflict",
                            detail=f"A price alert with term '{attrs.search_term}' already exists for this user",
                            source={"pointer": "/data/attributes/search_term"},
                        )
                    )

        return errors
