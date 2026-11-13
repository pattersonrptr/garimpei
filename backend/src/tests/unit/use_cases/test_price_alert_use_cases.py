"""Unit tests for PriceAlert Use Cases — SearchConfig linking logic (Issue #35)."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.use_cases import (
    CreatePriceAlertUseCase,
    DeletePriceAlertUseCase,
    GetPriceAlertByIdUseCase,
    GetPriceAlertsByUserIdUseCase,
    ListPriceAlertsUseCase,
    UpdatePriceAlertUseCase,
    _cleanup_orphaned_search_config,
    _find_or_create_search_config,
)
from src.app.entities.search_config import SearchConfig as SearchConfigEntity

# ============================================================================
# Helpers
# ============================================================================


def make_price_alert_entity(**overrides):
    defaults = {
        "id": 1,
        "search_term": "iPhone 13",
        "max_price": 2500.00,
        "is_active": True,
        "frequency_minutes": 60,
        "user_id": 1,
        "search_config_id": 10,
        "source_website_ids": [1, 2],
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 1),
    }
    defaults.update(overrides)
    return PriceAlertEntity(**defaults)


def make_search_config_entity(**overrides):
    defaults = {
        "id": 10,
        "search_term": "iPhone 13",
        "is_active": True,
        "frequency_days": 1,
        "user_id": 1,
        "source_website_ids": [1, 2],
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 1),
    }
    defaults.update(overrides)
    return SearchConfigEntity(**defaults)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_pa_repo():
    return Mock()


@pytest.fixture
def mock_sc_repo():
    return Mock()


# ============================================================================
# _find_or_create_search_config
# ============================================================================


class TestFindOrCreateSearchConfig:
    """Tests for the helper that links PriceAlert → SearchConfig."""

    def test_reuses_existing_active_config(self, mock_sc_repo):
        """When a matching active SearchConfig exists, returns its id."""
        existing = make_search_config_entity(id=10, is_active=True)
        mock_sc_repo.get_by_search_term_and_user_id.return_value = existing

        result = _find_or_create_search_config(mock_sc_repo, "iPhone 13", [1, 2], 1, 60)

        assert result == 10
        mock_sc_repo.create.assert_not_called()
        mock_sc_repo.update.assert_not_called()

    def test_reactivates_inactive_config(self, mock_sc_repo):
        """When a matching but inactive SearchConfig exists, reactivates it."""
        existing = make_search_config_entity(id=10, is_active=False)
        mock_sc_repo.get_by_search_term_and_user_id.return_value = existing

        result = _find_or_create_search_config(mock_sc_repo, "iPhone 13", [1, 2], 1, 60)

        assert result == 10
        mock_sc_repo.update.assert_called_once()
        updated = mock_sc_repo.update.call_args[0][1]
        assert updated.is_active is True

    def test_reactivated_config_takes_the_alerts_stores(self, mock_sc_repo):
        """
        Characterization (Nov 12, 2026): reactivating a paused SearchConfig
        replaces its stores with the alert's, not the ones it had before.
        """
        existing = make_search_config_entity(
            id=10, is_active=False, source_website_ids=[1, 2]
        )
        mock_sc_repo.get_by_search_term_and_user_id.return_value = existing

        _find_or_create_search_config(mock_sc_repo, "iPhone 13", [3], 1, 60)

        updated = mock_sc_repo.update.call_args[0][1]
        assert updated.source_website_ids == [3]

    def test_reactivated_config_takes_the_alerts_frequency(self, mock_sc_repo):
        """
        Characterization (Nov 12, 2026): reactivating a paused SearchConfig
        recomputes its frequency in days from the alert's minutes (rounded up).
        """
        existing = make_search_config_entity(id=10, is_active=False, frequency_days=1)
        mock_sc_repo.get_by_search_term_and_user_id.return_value = existing

        _find_or_create_search_config(mock_sc_repo, "iPhone 13", [1, 2], 1, 2881)

        updated = mock_sc_repo.update.call_args[0][1]
        assert updated.frequency_days == 3

    def test_creates_new_config_when_none_exists(self, mock_sc_repo):
        """When no matching SearchConfig exists, creates a new one."""
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        created = make_search_config_entity(id=42)
        mock_sc_repo.create.return_value = created

        result = _find_or_create_search_config(
            mock_sc_repo, "Samsung S23", [1], 2, 1440
        )

        assert result == 42
        mock_sc_repo.create.assert_called_once()
        config_arg = mock_sc_repo.create.call_args[0][0]
        assert config_arg.search_term == "Samsung S23"
        assert config_arg.user_id == 2
        assert config_arg.source_website_ids == [1]
        assert config_arg.is_active is True
        assert config_arg.frequency_days == 1

    def test_frequency_minutes_to_days_conversion(self, mock_sc_repo):
        """frequency_days = ceil(frequency_minutes / 1440), minimum 1."""
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        mock_sc_repo.create.return_value = make_search_config_entity(id=99)

        _find_or_create_search_config(mock_sc_repo, "test", [1], 1, 2880)

        config_arg = mock_sc_repo.create.call_args[0][0]
        assert config_arg.frequency_days == 2

    def test_frequency_minutes_rounds_up(self, mock_sc_repo):
        """1500 minutes → ceil(1500/1440) = 2 days."""
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        mock_sc_repo.create.return_value = make_search_config_entity(id=99)

        _find_or_create_search_config(mock_sc_repo, "test", [1], 1, 1500)

        config_arg = mock_sc_repo.create.call_args[0][0]
        assert config_arg.frequency_days == 2


# ============================================================================
# _cleanup_orphaned_search_config
# ============================================================================


class TestCleanupOrphanedSearchConfig:
    """Tests for orphaned SearchConfig deactivation."""

    def test_deactivates_config_when_no_active_alerts(self, mock_pa_repo, mock_sc_repo):
        """Deactivates SearchConfig if zero active alerts reference it."""
        mock_pa_repo.count_active_by_search_config_id.return_value = 0
        config = make_search_config_entity(id=10, is_active=True)
        mock_sc_repo.get_by_id.return_value = config

        _cleanup_orphaned_search_config(mock_pa_repo, mock_sc_repo, 10)

        mock_sc_repo.update.assert_called_once()
        updated = mock_sc_repo.update.call_args[0][1]
        assert updated.is_active is False

    def test_does_nothing_when_active_alerts_remain(self, mock_pa_repo, mock_sc_repo):
        """Keeps SearchConfig active if other alerts still reference it."""
        mock_pa_repo.count_active_by_search_config_id.return_value = 2

        _cleanup_orphaned_search_config(mock_pa_repo, mock_sc_repo, 10)

        mock_sc_repo.get_by_id.assert_not_called()
        mock_sc_repo.update.assert_not_called()

    def test_does_nothing_when_search_config_id_is_none(
        self, mock_pa_repo, mock_sc_repo
    ):
        """No-op when search_config_id is None."""
        _cleanup_orphaned_search_config(mock_pa_repo, mock_sc_repo, None)

        mock_pa_repo.count_active_by_search_config_id.assert_not_called()

    def test_does_nothing_when_config_already_inactive(
        self, mock_pa_repo, mock_sc_repo
    ):
        """No-op when SearchConfig is already inactive."""
        mock_pa_repo.count_active_by_search_config_id.return_value = 0
        config = make_search_config_entity(id=10, is_active=False)
        mock_sc_repo.get_by_id.return_value = config

        _cleanup_orphaned_search_config(mock_pa_repo, mock_sc_repo, 10)

        mock_sc_repo.update.assert_not_called()


# ============================================================================
# CreatePriceAlertUseCase
# ============================================================================


class TestCreatePriceAlertUseCase:
    """Tests for CreatePriceAlertUseCase with SearchConfig linking."""

    def test_creates_alert_with_new_search_config(self, mock_pa_repo, mock_sc_repo):
        """
        Given: No existing SearchConfig for this search_term + user
        When: Creating a PriceAlert
        Then: A new SearchConfig is created, and the alert links to it
        """
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        mock_sc_repo.create.return_value = make_search_config_entity(id=42)

        new_alert = PriceAlertEntity(
            search_term="Samsung S23",
            max_price=1800.00,
            user_id=2,
            source_website_ids=[1],
        )
        created_alert = make_price_alert_entity(
            id=5, search_term="Samsung S23", search_config_id=42
        )
        mock_pa_repo.create.return_value = created_alert

        uc = CreatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(new_alert)

        assert mock_pa_repo.create.call_args[0][0].search_config_id == 42
        assert result == created_alert

    def test_creates_alert_reusing_existing_config(self, mock_pa_repo, mock_sc_repo):
        """
        Given: Existing active SearchConfig for this search_term + user
        When: Creating a PriceAlert
        Then: The existing SearchConfig is reused
        """
        existing_config = make_search_config_entity(id=10, is_active=True)
        mock_sc_repo.get_by_search_term_and_user_id.return_value = existing_config

        new_alert = PriceAlertEntity(
            search_term="iPhone 13",
            max_price=2500.00,
            user_id=1,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.create.return_value = make_price_alert_entity(search_config_id=10)

        uc = CreatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        uc.execute(new_alert)

        mock_sc_repo.create.assert_not_called()
        assert mock_pa_repo.create.call_args[0][0].search_config_id == 10


# ============================================================================
# UpdatePriceAlertUseCase
# ============================================================================


class TestUpdatePriceAlertUseCase:
    """Tests for UpdatePriceAlertUseCase with SearchConfig re-linking."""

    def test_keeps_same_config_when_term_unchanged(self, mock_pa_repo, mock_sc_repo):
        """
        Given: Alert update with same search_term and source_website_ids
        When: execute is called
        Then: search_config_id stays the same, no re-link
        """
        existing = make_price_alert_entity(
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.get_by_id.return_value = existing

        updated_entity = make_price_alert_entity(
            max_price=3000.00,
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.update.return_value = updated_entity

        uc = UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(1, updated_entity)

        mock_sc_repo.get_by_search_term_and_user_id.assert_not_called()
        assert result.search_config_id == 10

    def test_relinks_config_when_search_term_changes(self, mock_pa_repo, mock_sc_repo):
        """
        Given: Alert update with different search_term
        When: execute is called
        Then: A new SearchConfig is found/created and old one cleaned up
        """
        existing = make_price_alert_entity(
            search_term="iPhone 13",
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.get_by_id.return_value = existing

        new_config = make_search_config_entity(id=20, search_term="iPhone 14")
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        mock_sc_repo.create.return_value = new_config

        updated_entity = make_price_alert_entity(
            search_term="iPhone 14",
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.update.return_value = make_price_alert_entity(
            search_term="iPhone 14", search_config_id=20
        )
        mock_pa_repo.count_active_by_search_config_id.return_value = 0
        old_config = make_search_config_entity(id=10, is_active=True)
        mock_sc_repo.get_by_id.return_value = old_config

        uc = UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(1, updated_entity)

        mock_sc_repo.update.assert_called()
        assert result.search_config_id == 20

    def test_relinks_config_when_stores_change(self, mock_pa_repo, mock_sc_repo):
        """
        Characterization (Nov 12, 2026): same term, different stores: the
        alert is linked to a SearchConfig found or created for the new stores.
        """
        existing = make_price_alert_entity(search_config_id=10, source_website_ids=[1])
        mock_pa_repo.get_by_id.return_value = existing
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        mock_sc_repo.create.return_value = make_search_config_entity(id=20)
        mock_pa_repo.count_active_by_search_config_id.return_value = 1
        changed = make_price_alert_entity(
            search_config_id=10, source_website_ids=[1, 3]
        )

        UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo).execute(1, changed)

        created = mock_sc_repo.create.call_args[0][0]
        assert created.source_website_ids == [1, 3]
        saved = mock_pa_repo.update.call_args[0][1]
        assert saved.search_config_id == 20

    def test_same_stores_in_another_order_keep_the_config(
        self, mock_pa_repo, mock_sc_repo
    ):
        """
        Characterization (Nov 12, 2026): store order does not count as a
        change, so the alert keeps its SearchConfig.
        """
        existing = make_price_alert_entity(
            search_config_id=10, source_website_ids=[1, 2]
        )
        mock_pa_repo.get_by_id.return_value = existing
        changed = make_price_alert_entity(
            search_config_id=10, source_website_ids=[2, 1]
        )

        UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo).execute(1, changed)

        mock_sc_repo.get_by_search_term_and_user_id.assert_not_called()
        saved = mock_pa_repo.update.call_args[0][1]
        assert saved.search_config_id == 10

    def test_deactivation_cleans_up_orphaned_config(self, mock_pa_repo, mock_sc_repo):
        """
        Given: Alert is being deactivated (is_active=True → False)
        When: No other active alerts use the same SearchConfig
        Then: SearchConfig is deactivated
        """
        existing = make_price_alert_entity(
            is_active=True,
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.get_by_id.return_value = existing

        deactivated = make_price_alert_entity(
            is_active=False,
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.update.return_value = deactivated
        mock_pa_repo.count_active_by_search_config_id.return_value = 0
        config = make_search_config_entity(id=10, is_active=True)
        mock_sc_repo.get_by_id.return_value = config

        uc = UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        uc.execute(1, deactivated)

        mock_pa_repo.count_active_by_search_config_id.assert_called_with(10)
        update_call = mock_sc_repo.update.call_args
        assert update_call[0][1].is_active is False

    def test_deactivation_keeps_config_if_other_alerts_exist(
        self, mock_pa_repo, mock_sc_repo
    ):
        """
        Given: Alert is being deactivated
        When: Other active alerts still reference the same SearchConfig
        Then: SearchConfig stays active
        """
        existing = make_price_alert_entity(
            is_active=True,
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.get_by_id.return_value = existing

        deactivated = make_price_alert_entity(
            is_active=False,
            search_config_id=10,
            source_website_ids=[1, 2],
        )
        mock_pa_repo.update.return_value = deactivated
        mock_pa_repo.count_active_by_search_config_id.return_value = 1

        uc = UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        uc.execute(1, deactivated)

        mock_sc_repo.get_by_id.assert_not_called()

    def test_returns_none_when_alert_not_found(self, mock_pa_repo, mock_sc_repo):
        """Returns None when the alert does not exist."""
        mock_pa_repo.get_by_id.return_value = None

        uc = UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(999, make_price_alert_entity())

        assert result is None

    def test_book_alert_update_never_links_a_search_config(
        self, mock_pa_repo, mock_sc_repo
    ):
        """
        Characterization (Nov 12, 2026): a book alert has no SearchConfig.
        Even when its term changes, no config is looked up or created, and it
        is saved with search_config_id None.
        """
        existing = make_price_alert_entity(
            canonical_product_id=5, search_config_id=None, search_term="Dom Casmurro"
        )
        mock_pa_repo.get_by_id.return_value = existing
        changed = make_price_alert_entity(
            canonical_product_id=5, search_config_id=99, search_term="Memórias"
        )

        uc = UpdatePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        uc.execute(1, changed)

        saved = mock_pa_repo.update.call_args.args[1]
        assert saved.search_config_id is None
        mock_sc_repo.get_by_search_term_and_user_id.assert_not_called()
        mock_sc_repo.create.assert_not_called()


# ============================================================================
# DeletePriceAlertUseCase
# ============================================================================


class TestDeletePriceAlertUseCase:
    """Tests for DeletePriceAlertUseCase with orphan cleanup."""

    def test_deletes_alert_and_cleans_up_orphaned_config(
        self, mock_pa_repo, mock_sc_repo
    ):
        """
        Given: Deleting the last alert that uses a SearchConfig
        When: execute is called
        Then: Alert is deleted and SearchConfig deactivated
        """
        existing = make_price_alert_entity(search_config_id=10)
        mock_pa_repo.get_by_id.return_value = existing
        mock_pa_repo.delete.return_value = True
        mock_pa_repo.count_active_by_search_config_id.return_value = 0
        config = make_search_config_entity(id=10, is_active=True)
        mock_sc_repo.get_by_id.return_value = config

        uc = DeletePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(1)

        assert result is True
        mock_pa_repo.delete.assert_called_once_with(1)
        update_call = mock_sc_repo.update.call_args
        assert update_call[0][1].is_active is False

    def test_deletes_alert_without_cleanup_if_other_alerts_remain(
        self, mock_pa_repo, mock_sc_repo
    ):
        """
        Given: Deleting an alert that shares its SearchConfig with others
        When: execute is called
        Then: Alert is deleted but SearchConfig stays active
        """
        existing = make_price_alert_entity(search_config_id=10)
        mock_pa_repo.get_by_id.return_value = existing
        mock_pa_repo.delete.return_value = True
        mock_pa_repo.count_active_by_search_config_id.return_value = 2

        uc = DeletePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(1)

        assert result is True
        mock_sc_repo.get_by_id.assert_not_called()

    def test_returns_false_when_alert_not_found(self, mock_pa_repo, mock_sc_repo):
        """Returns False when the alert does not exist."""
        mock_pa_repo.get_by_id.return_value = None

        uc = DeletePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(999)

        assert result is False
        mock_pa_repo.delete.assert_not_called()

    def test_no_cleanup_when_search_config_id_is_none(self, mock_pa_repo, mock_sc_repo):
        """No cleanup attempt when alert has no linked SearchConfig."""
        existing = make_price_alert_entity(search_config_id=None)
        mock_pa_repo.get_by_id.return_value = existing
        mock_pa_repo.delete.return_value = True

        uc = DeletePriceAlertUseCase(mock_pa_repo, mock_sc_repo)
        result = uc.execute(1)

        assert result is True
        mock_pa_repo.count_active_by_search_config_id.assert_not_called()


# ============================================================================
# GetPriceAlertByIdUseCase (unchanged interface — sanity check)
# ============================================================================


class TestGetPriceAlertByIdUseCase:
    """Tests for GetPriceAlertByIdUseCase."""

    def test_returns_entity_when_found(self, mock_pa_repo):
        entity = make_price_alert_entity()
        mock_pa_repo.get_by_id.return_value = entity

        result = GetPriceAlertByIdUseCase(mock_pa_repo).execute(1)

        assert result == entity

    def test_returns_none_when_not_found(self, mock_pa_repo):
        mock_pa_repo.get_by_id.return_value = None

        result = GetPriceAlertByIdUseCase(mock_pa_repo).execute(999)

        assert result is None


# ============================================================================
# GetPriceAlertsByUserIdUseCase (unchanged — sanity check)
# ============================================================================


class TestGetPriceAlertsByUserIdUseCase:
    """Tests for GetPriceAlertsByUserIdUseCase."""

    def test_returns_list(self, mock_pa_repo):
        entity = make_price_alert_entity()
        mock_pa_repo.get_by_user_id.return_value = [entity]

        result = GetPriceAlertsByUserIdUseCase(mock_pa_repo).execute(1)

        assert result == [entity]


# ============================================================================
# ListPriceAlertsUseCase (unchanged — sanity check)
# ============================================================================


class TestListPriceAlertsUseCase:
    """Tests for ListPriceAlertsUseCase."""

    def test_returns_paginated_result(self, mock_pa_repo):
        entity = make_price_alert_entity()
        mock_pa_repo.get_all.return_value = ([entity], 1)

        result, total = ListPriceAlertsUseCase(mock_pa_repo).execute(limit=10, offset=0)

        assert total == 1
        assert result == [entity]
