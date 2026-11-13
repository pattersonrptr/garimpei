"""Characterization tests for NotifyAlertOpportunitiesUseCase (keyword alerts).

Written Nov 12, 2026, before moving alerts off the old ``src/app/interfaces``
ports: they pin today's behavior of the store-name lookup and the listings
without a price, which no other test covered.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from src.app.alerts.entities import Listing
from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.use_cases import NotifyAlertOpportunitiesUseCase


def make_keyword_alert() -> PriceAlertEntity:
    return PriceAlertEntity(
        id=1,
        search_term="iPhone 13",
        max_price=2500.00,
        is_active=True,
        user_id=7,
        source_website_ids=[1],
    )


def make_listing(product_id: int, source_website_id: int = 1, price=2000.00):
    return Listing(
        id=product_id,
        url=f"https://example.com/product/{product_id}",
        title=f"iPhone 13 #{product_id}",
        store_id=source_website_id,
        price=price,
        condition="undetermined",
        is_available=True,
    )


def make_use_case(listings, stores):
    """The use case over fakes that send every e-mail successfully."""
    product_repo = Mock()
    product_repo.opportunities_for_alert.return_value = listings
    notification_log_repo = Mock()
    notification_log_repo.exists_for_alert_and_product.return_value = False
    notification_log_repo.create.side_effect = lambda log: log
    user_repo = Mock()
    user_repo.get_by_id.return_value = SimpleNamespace(email="owner@example.com")
    source_website_repo = Mock()
    source_website_repo.get_by_id.side_effect = stores.get
    email_service = Mock()
    email_service.send_price_alert_email.return_value = SimpleNamespace(
        success=True, error_message=None
    )
    use_case = NotifyAlertOpportunitiesUseCase(
        product_repo,
        Mock(),
        notification_log_repo,
        user_repo,
        source_website_repo,
        email_service,
    )
    return use_case, source_website_repo, email_service


def emailed_store_names(email_service) -> list[str]:
    return [
        call.kwargs["source_website_name"]
        for call in email_service.send_price_alert_email.call_args_list
    ]


def test_store_is_looked_up_once_for_listings_from_the_same_store():
    olx = SimpleNamespace(name="OLX")
    use_case, source_website_repo, email_service = make_use_case(
        [make_listing(10), make_listing(11)], {1: olx}
    )

    sent = use_case.execute(make_keyword_alert())

    assert len(sent) == 2
    assert emailed_store_names(email_service) == ["OLX", "OLX"]
    source_website_repo.get_by_id.assert_called_once_with(1)


def test_listing_without_a_current_price_is_not_notified():
    olx = SimpleNamespace(name="OLX")
    use_case, _, email_service = make_use_case(
        [make_listing(10, price=None), make_listing(11)], {1: olx}
    )

    sent = use_case.execute(make_keyword_alert())

    assert len(sent) == 1
    titles = [
        call.kwargs["product_title"]
        for call in email_service.send_price_alert_email.call_args_list
    ]
    assert titles == ["iPhone 13 #11"]


def test_store_that_no_longer_exists_is_named_unknown():
    use_case, _, email_service = make_use_case([make_listing(10, 404)], {})

    use_case.execute(make_keyword_alert())

    assert emailed_store_names(email_service) == ["Unknown"]
