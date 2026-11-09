"""
E2E Test Configuration

Provides fixtures for end-to-end testing with:
- Test database setup (SQLite in-memory)
- FastAPI TestClient
- Authentication helpers
- Sample data creation
"""

import os

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Disable file logging for tests
os.environ["ENABLE_FILE_LOGGING"] = "false"

# Import models first so they register with Base.metadata before create_all()
from src.app.catalog.persistence.models import (
    PriceHistory as PriceHistoryModel,  # noqa: F401
)
from src.app.catalog.persistence.models import (
    Product as ProductModel,  # noqa: F401
)
from src.app.infrastructure.database.models.notification_log_model import (
    NotificationLog as NotificationLogModel,  # noqa: F401
)
from src.app.infrastructure.database.models.plan_model import (
    Plan as PlanModel,  # noqa: F401
)
from src.app.infrastructure.database.models.price_alert_model import (
    PriceAlert as PriceAlertModel,  # noqa: F401
)
from src.app.infrastructure.database.models.price_alert_source_website_model import (  # noqa: F401
    price_alert_source_website,
)
from src.app.infrastructure.database.models.search_config_model import (  # noqa: F401
    SearchConfig as SearchConfigModel,
)
from src.app.infrastructure.database.models.search_config_source_website_model import (  # noqa: F401
    search_config_source_website,
)
from src.app.infrastructure.database.models.search_execution_log_model import (  # noqa: F401
    SearchExecutionLog as SearchExecutionLogModel,
)
from src.app.infrastructure.database.models.source_website_model import (  # noqa: F401
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database.models.subscription_model import (
    Subscription as SubscriptionModel,  # noqa: F401
)
from src.app.infrastructure.database.models.user_model import User  # noqa: F401

# Then import database config and app
from src.app.infrastructure.database_config import Base, get_db
from src.main import app

# Password hashing context (same as in use_cases)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh SQLite in-memory database for each test.

    Given: A test requiring database access
    When: Test is executed
    Then: Provides isolated database session with clean state

    Note: The User model import above is critical - it registers the model
    with SQLAlchemy's Base.metadata before create_all() is called.
    """
    # Ensure all models are imported to register with Base.metadata
    from src.app.catalog.persistence.models import (  # noqa: F401
        Product as ProductModel,
    )
    from src.app.infrastructure.database.models.source_website_model import (  # noqa: F401
        SourceWebsite as SourceWebsiteModel,
    )
    from src.app.infrastructure.database.models.user_model import User  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False
        },  # Allow SQLite to work with FastAPI's async
        poolclass=StaticPool,  # CRITICAL: Use StaticPool to maintain single connection for in-memory DB
    )

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,  # Don't expire objects after commit, avoiding extra queries
    )
    session = TestingSessionLocal()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def client(test_db):
    """
    FastAPI TestClient with overridden database dependency.

    Given: A test requiring HTTP requests
    When: Test is executed
    Then: Provides TestClient with isolated test database
    """

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def sample_user(test_db):
    """
    Create a sample user in the database.

    Credentials:
        username: testuser
        email: test@example.com
        password: Test@1234
        is_superuser: False
    """
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=pwd_context.hash("Test@1234"),
        is_superuser=False,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_superuser(test_db):
    """
    Create a sample superuser in the database.

    Credentials:
        username: admin
        email: admin@example.com
        password: Admin@1234
        is_superuser: True
    """
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=pwd_context.hash("Admin@1234"),
        is_superuser=True,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def user_token(client, sample_user):
    """
    Get authentication token for regular user.

    Returns:
        str: Bearer token for testuser
    """
    response = client.post(
        "/auth/login", data={"username": "testuser", "password": "Test@1234"}
    )
    assert response.status_code == 200
    token = response.json()["data"]["attributes"]["access_token"]
    return token


@pytest.fixture(scope="function")
def superuser_token(client, sample_superuser):
    """
    Get authentication token for superuser.

    Returns:
        str: Bearer token for admin
    """
    response = client.post(
        "/auth/login", data={"username": "admin", "password": "Admin@1234"}
    )
    assert response.status_code == 200
    token = response.json()["data"]["attributes"]["access_token"]
    return token


@pytest.fixture(scope="function")
def auth_headers(user_token):
    """
    Get authorization headers with user token.

    Returns:
        dict: Headers with Authorization: Bearer <token>
    """
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def superuser_auth_headers(superuser_token):
    """
    Get authorization headers with superuser token.

    Returns:
        dict: Headers with Authorization: Bearer <token>
    """
    return {"Authorization": f"Bearer {superuser_token}"}


# ============================================================================
# PRODUCT-RELATED FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def sample_staff_user(test_db):
    """
    Create a staff (non-superuser) user in the database.

    Credentials:
        username: staffuser
        email: staff@example.com
        password: Staff@1234
        is_staff: True
        is_superuser: False
    """
    user = User(
        username="staffuser",
        email="staff@example.com",
        hashed_password=pwd_context.hash("Staff@1234"),
        is_superuser=False,
        is_staff=True,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def staff_token(client, sample_staff_user):
    """
    Get authentication token for staff user.

    Returns:
        str: Bearer token for staffuser
    """
    response = client.post(
        "/auth/login", data={"username": "staffuser", "password": "Staff@1234"}
    )
    assert response.status_code == 200
    token = response.json()["data"]["attributes"]["access_token"]
    return token


@pytest.fixture(scope="function")
def staff_auth_headers(staff_token):
    """
    Get authorization headers with staff token.

    Returns:
        dict: Headers with Authorization: Bearer <token>
    """
    return {"Authorization": f"Bearer {staff_token}"}


@pytest.fixture(scope="function")
def sample_source_website(test_db):
    """
    Create a sample source website in the database (required FK for products).

    Returns:
        SourceWebsiteModel: Persisted SourceWebsite instance
    """
    website = SourceWebsiteModel(
        name="Test Website",
        base_url="https://test.example.com",
        is_active=True,
    )
    test_db.add(website)
    test_db.commit()
    test_db.refresh(website)
    return website


@pytest.fixture(scope="function")
def sample_product(test_db, sample_source_website):
    """
    Create a sample product in the database.

    Returns:
        ProductModel: Persisted Product instance
    """
    from src.app.catalog.entities import ProductCondition

    product = ProductModel(
        url="https://test.example.com/product/123",
        title="Test Product",
        source_product_code="test-123",
        description="A test product description",
        condition=ProductCondition.NEW,
        is_available=True,
        source_website_id=sample_source_website.id,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)
    return product


@pytest.fixture(scope="function")
def sample_search_config(test_db, sample_user):
    """
    Create a sample search config in the database.

    Returns:
        SearchConfigModel: Persisted SearchConfig instance
    """

    config = SearchConfigModel(
        search_term="laptop",
        is_active=True,
        frequency_days=1,
        user_id=sample_user.id,
    )
    test_db.add(config)
    test_db.commit()
    test_db.refresh(config)
    return config


@pytest.fixture(scope="function")
def sample_search_execution_log(test_db, sample_search_config):
    """
    Create a sample search execution log in the database.

    Returns:
        SearchExecutionLogModel: Persisted SearchExecutionLog instance
    """

    log = SearchExecutionLogModel(
        search_config_id=sample_search_config.id,
        status="success",
        results_count=3,
    )
    test_db.add(log)
    test_db.commit()
    test_db.refresh(log)
    return log
