"""Integration tests for SearchConfigKeywordSearches (alerts' KeywordSearches port).

The adapter alerts uses to create, reactivate and pause the collector
searches behind keyword alerts, over the real SearchConfig repository and
an in-memory SQLite database.
"""

from datetime import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.alerts.entities import KeywordSearch
from src.app.alerts.persistence.keyword_searches import SearchConfigKeywordSearches
from src.app.entities.search_config import SearchConfig as SearchConfigEntity

# Import all models to register with Base.metadata
from src.app.infrastructure.database.models.search_config_model import (  # noqa: F401
    SearchConfig as SearchConfigModel,
)
from src.app.infrastructure.database.models.search_config_source_website_model import (  # noqa: F401
    search_config_source_website,
)
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database.models.user_model import User
from src.app.infrastructure.database_config import Base
from src.app.infrastructure.repositories.search_config_repository import (
    SearchConfigRepository,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def user_id(db):
    user = User(
        username="owner", email="owner@example.com", hashed_password="x", is_active=True
    )
    db.add(user)
    db.commit()
    return user.id


@pytest.fixture
def store_ids(db):
    stores = [
        SourceWebsiteModel(name="OLX", base_url="https://www.olx.com.br"),
        SourceWebsiteModel(name="Enjoei", base_url="https://www.enjoei.com.br"),
    ]
    db.add_all(stores)
    db.commit()
    return [store.id for store in stores]


@pytest.fixture
def configs(db):
    return SearchConfigRepository(db)


@pytest.fixture
def searches(configs):
    return SearchConfigKeywordSearches(configs)


def test_created_search_is_saved_with_its_stores(searches, configs, user_id, store_ids):
    created = searches.create(
        KeywordSearch(
            search_term="iPhone 13",
            frequency_days=2,
            user_id=user_id,
            source_website_ids=store_ids,
        )
    )

    saved = configs.get_by_id(created.id)
    assert saved.search_term == "iPhone 13"
    assert saved.is_active is True
    assert saved.frequency_days == 2
    assert sorted(saved.source_website_ids) == sorted(store_ids)


def test_finds_the_users_search_by_term(searches, configs, user_id, store_ids):
    existing = configs.create(
        SearchConfigEntity(
            search_term="iPhone 13", user_id=user_id, source_website_ids=store_ids[:1]
        )
    )

    found = searches.get_by_search_term_and_user_id("iPhone 13", user_id)

    assert found.id == existing.id
    assert found.source_website_ids == store_ids[:1]


def test_pausing_a_search_is_saved(searches, configs, user_id):
    existing = configs.create(
        SearchConfigEntity(search_term="iPhone 13", user_id=user_id)
    )
    search = searches.get_by_id(existing.id)
    search.is_active = False

    searches.update(existing.id, search)

    assert configs.get_by_id(existing.id).is_active is False


def test_new_stores_and_frequency_are_saved(searches, configs, user_id, store_ids):
    existing = configs.create(
        SearchConfigEntity(
            search_term="iPhone 13", user_id=user_id, source_website_ids=store_ids[:1]
        )
    )
    search = searches.get_by_id(existing.id)
    search.source_website_ids = store_ids[1:]
    search.frequency_days = 3

    searches.update(existing.id, search)

    saved = configs.get_by_id(existing.id)
    assert saved.source_website_ids == store_ids[1:]
    assert saved.frequency_days == 3


def test_update_keeps_the_fields_alerts_does_not_know(searches, configs, user_id):
    existing = configs.create(
        SearchConfigEntity(
            search_term="iPhone 13",
            user_id=user_id,
            preferred_time=time(8, 30),
            search_metadata={"origin": "admin"},
        )
    )
    search = searches.get_by_id(existing.id)
    search.is_active = False

    searches.update(existing.id, search)

    saved = configs.get_by_id(existing.id)
    assert saved.preferred_time == time(8, 30)
    assert saved.search_metadata == {"origin": "admin"}


def test_update_of_a_missing_search_returns_none(searches, user_id):
    assert searches.update(999, KeywordSearch(search_term="x", user_id=user_id)) is None
