from src.app.catalog.http.product_schema import (
    ProductCreateRequest,
    ProductUpdateRequest,
)
from src.app.catalog.ports import (
    PriceHistoryRepositoryInterface,
    ProductRepositoryInterface,
)
from src.common.jsonapi import JsonApiError


class ProductValidator:
    def __init__(self, product_repo: ProductRepositoryInterface):
        self.product_repo = product_repo

    def validate_create_request(
        self, product_in: ProductCreateRequest
    ) -> list[JsonApiError]:
        """
        Validates a product creation request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "product"
        if product_in.data.type != "product":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'product', got '{product_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = product_in.data.attributes

        # Validation 2: URL required
        if not attrs.url or not attrs.url.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'url' is required",
                    source={"pointer": "/data/attributes/url"},
                )
            )

        # Validation 3: title required
        if not attrs.title or not attrs.title.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'title' is required",
                    source={"pointer": "/data/attributes/title"},
                )
            )

        # Validation 4: source_website_id required
        if attrs.source_website_id is None:
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'source_website_id' is required",
                    source={"pointer": "/data/attributes/source_website_id"},
                )
            )

        # If there are required field errors, return early (don't validate duplicates)
        if errors:
            return errors

        # Validation 5: URL already exists
        if attrs.url:
            existing_product = self.product_repo.get_by_url(attrs.url)
            if existing_product:
                errors.append(
                    JsonApiError(
                        status="409",
                        code="DUPLICATE_URL",
                        title="Conflict",
                        detail=f"A product with URL '{attrs.url}' already exists",
                        source={"pointer": "/data/attributes/url"},
                    )
                )

        return errors

    def validate_update_request(
        self, product_id: int, product_in: ProductUpdateRequest
    ) -> list[JsonApiError]:
        """
        Validates a product update request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "product"
        if product_in.data.type != "product":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'product', got '{product_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = product_in.data.attributes

        # Validation 2: title cannot be empty if provided
        if attrs.title is not None and not attrs.title.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_VALUE",
                    title="Validation error",
                    detail="Field 'title' cannot be empty",
                    source={"pointer": "/data/attributes/title"},
                )
            )

        # Validation 3: URL cannot be changed to a duplicate if provided
        if attrs.url is not None:
            if not attrs.url.strip():
                errors.append(
                    JsonApiError(
                        status="422",
                        code="INVALID_VALUE",
                        title="Validation error",
                        detail="Field 'url' cannot be empty",
                        source={"pointer": "/data/attributes/url"},
                    )
                )
            else:
                # Check if URL is being changed to a different product's URL
                existing_product = self.product_repo.get_by_url(attrs.url)
                if existing_product and existing_product.id != product_id:
                    errors.append(
                        JsonApiError(
                            status="409",
                            code="DUPLICATE_URL",
                            title="Conflict",
                            detail=f"A product with URL '{attrs.url}' already exists",
                            source={"pointer": "/data/attributes/url"},
                        )
                    )

        return errors


class PriceHistoryValidator:
    """Validates price history create requests."""

    def __init__(
        self,
        price_history_repo: PriceHistoryRepositoryInterface,
        product_repo: ProductRepositoryInterface,
    ):
        self.price_history_repo = price_history_repo
        self.product_repo = product_repo

    def validate_create_request(self, price_history_in) -> list[JsonApiError]:
        """
        Validates a price history creation request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "price_history"
        if price_history_in.data.type != "price_history":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'price_history', got '{price_history_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = price_history_in.data.attributes

        # Validation 2: product_id required and positive
        if attrs.product_id is None or attrs.product_id <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'product_id' must be a positive integer",
                    source={"pointer": "/data/attributes/product_id"},
                )
            )

        # Validation 3: price required and positive
        if attrs.price is None or attrs.price <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'price' must be a positive number",
                    source={"pointer": "/data/attributes/price"},
                )
            )

        # Return early if field-level errors
        if errors:
            return errors

        # Validation 4: referenced product must exist
        existing_product = self.product_repo.get_by_id(attrs.product_id)
        if not existing_product:
            errors.append(
                JsonApiError(
                    status="404",
                    code="PRODUCT_NOT_FOUND",
                    title="Related resource not found",
                    detail=f"Product with id '{attrs.product_id}' does not exist",
                    source={"pointer": "/data/attributes/product_id"},
                )
            )

        return errors
