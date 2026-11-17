"""A plan limit an alert breaks, as a JSON:API error."""

from src.app.alerts.entities import LimitViolation
from src.common.jsonapi import JsonApiError


def limit_error(violation: LimitViolation) -> JsonApiError:
    return JsonApiError(
        status="403",
        code="PLAN_LIMIT_REACHED",
        title=violation.title,
        detail=violation.detail,
        source={"pointer": violation.pointer},
        meta=violation.meta,
    )
