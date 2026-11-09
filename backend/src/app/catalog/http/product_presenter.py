from fastapi.responses import JSONResponse

from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.http.product_schema import (
    ProductReadResponse,
    ProductResource,
    ProductsCollectionResponse,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class ProductPresenter:
    """
    Presenter for Product entities following Clean Architecture.
    Transforms domain entities into HTTP presentation formats (JSON:API).
    """

    @staticmethod
    def handle_validation_errors(validation_errors: list) -> JSONResponse:
        """
        Returns validation errors in JSON:API format.
        """
        first_error = validation_errors[0]
        status_code = int(first_error.status)
        return JSONResponse(
            status_code=status_code,
            content=JsonApiErrorResponse(errors=validation_errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_not_found(identifier: str, pointer: str = "/data") -> JSONResponse:
        """
        Returns 404 in JSON:API format.
        """
        errors = [
            JsonApiError(
                status="404",
                code="NOT_FOUND",
                title="Product not found",
                detail=f"Product with {identifier} not found",
                source={"pointer": pointer},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_conflict(detail: str) -> JSONResponse:
        """
        Returns 409 Conflict in JSON:API format.
        """
        errors = [
            JsonApiError(
                status="409",
                code="CONFLICT",
                title="Resource conflict",
                detail=detail,
                source={"pointer": "/data/attributes/url"},
            )
        ]
        return JSONResponse(
            status_code=409,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_success(entity: ProductEntity) -> ProductReadResponse:
        """
        Returns product in JSON:API format (success).
        """
        return ProductReadResponse(data=ProductResource.from_entity(entity))

    @staticmethod
    def handle_collection_success(
        entities: list[ProductEntity], total: int
    ) -> ProductsCollectionResponse:
        """
        Returns collection of products in JSON:API format.
        Includes meta with total count for pagination.
        """
        response = ProductsCollectionResponse(
            data=[ProductResource.from_entity(entity) for entity in entities],
            meta={"total": total},
        )
        return response
