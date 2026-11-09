"""
Unit tests for Product Use Cases.

Tests business logic layer with mocked repositories.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.entities import ProductCondition
from src.app.catalog.use_cases import (
    CreateProductUseCase,
    DeleteProductUseCase,
    GetProductByIdUseCase,
    GetProductByUrlUseCase,
    ListProductsUseCase,
    UpdateProductUseCase,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_product_repo():
    """Mock repository for testing use cases in isolation."""
    return Mock()


@pytest.fixture
def sample_product_entity():
    """Sample product entity for testing."""
    return ProductEntity(
        id=1,
        url="https://www.olx.com.br/item/iphone-13",
        title="iPhone 13 128GB",
        source_product_code="OLX-123",
        description="iPhone em ótimo estado",
        condition=ProductCondition.USED,
        seller_name="João Silva",
        is_available=True,
        source_website_id=1,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_new_product_entity():
    """Sample product entity without ID (for creation)."""
    return ProductEntity(
        url="https://www.olx.com.br/item/iphone-14",
        title="iPhone 14 256GB",
        source_product_code="OLX-456",
        condition=ProductCondition.NEW,
        is_available=True,
        source_website_id=1,
    )


# ============================================================================
# CreateProductUseCase Tests
# ============================================================================


class TestCreateProductUseCase:
    """Tests for CreateProductUseCase."""

    def test_execute_should_create_product_and_return_entity(
        self, mock_product_repo, sample_new_product_entity, sample_product_entity
    ):
        """
        Given: A valid product entity
        When: execute() is called
        Then: Should delegate to repository and return the created product
        """
        # Arrange
        mock_product_repo.create.return_value = sample_product_entity
        use_case = CreateProductUseCase(mock_product_repo)

        # Act
        result = use_case.execute(sample_new_product_entity)

        # Assert
        assert result == sample_product_entity
        assert result.id == 1
        mock_product_repo.create.assert_called_once_with(sample_new_product_entity)

    def test_execute_should_return_product_with_generated_id(
        self, mock_product_repo, sample_new_product_entity
    ):
        """
        Given: A product entity without an ID
        When: execute() is called
        Then: The returned product should have a generated ID
        """
        # Arrange
        created_with_id = ProductEntity(
            id=42,
            url=sample_new_product_entity.url,
            title=sample_new_product_entity.title,
            source_website_id=1,
            condition=ProductCondition.NEW,
            is_available=True,
        )
        mock_product_repo.create.return_value = created_with_id
        use_case = CreateProductUseCase(mock_product_repo)

        # Act
        result = use_case.execute(sample_new_product_entity)

        # Assert
        assert result.id == 42


# ============================================================================
# GetProductByIdUseCase Tests
# ============================================================================


class TestGetProductByIdUseCase:
    """Tests for GetProductByIdUseCase."""

    def test_execute_with_existing_id_should_return_product(
        self, mock_product_repo, sample_product_entity
    ):
        """
        Given: An existing product ID
        When: execute() is called
        Then: Should return the corresponding ProductEntity
        """
        # Arrange
        mock_product_repo.get_by_id.return_value = sample_product_entity
        use_case = GetProductByIdUseCase(mock_product_repo)

        # Act
        result = use_case.execute(1)

        # Assert
        assert result == sample_product_entity
        mock_product_repo.get_by_id.assert_called_once_with(1)

    def test_execute_with_nonexistent_id_should_return_none(self, mock_product_repo):
        """
        Given: A non-existent product ID
        When: execute() is called
        Then: Should return None
        """
        # Arrange
        mock_product_repo.get_by_id.return_value = None
        use_case = GetProductByIdUseCase(mock_product_repo)

        # Act
        result = use_case.execute(999)

        # Assert
        assert result is None
        mock_product_repo.get_by_id.assert_called_once_with(999)


# ============================================================================
# GetProductByUrlUseCase Tests
# ============================================================================


class TestGetProductByUrlUseCase:
    """Tests for GetProductByUrlUseCase."""

    def test_execute_with_existing_url_should_return_product(
        self, mock_product_repo, sample_product_entity
    ):
        """
        Given: A URL matching an existing product
        When: execute() is called
        Then: Should return the corresponding ProductEntity
        """
        # Arrange
        url = "https://www.olx.com.br/item/iphone-13"
        mock_product_repo.get_by_url.return_value = sample_product_entity
        use_case = GetProductByUrlUseCase(mock_product_repo)

        # Act
        result = use_case.execute(url)

        # Assert
        assert result == sample_product_entity
        mock_product_repo.get_by_url.assert_called_once_with(url)

    def test_execute_with_nonexistent_url_should_return_none(self, mock_product_repo):
        """
        Given: A URL that does not match any product
        When: execute() is called
        Then: Should return None
        """
        # Arrange
        mock_product_repo.get_by_url.return_value = None
        use_case = GetProductByUrlUseCase(mock_product_repo)

        # Act
        result = use_case.execute("https://www.olx.com.br/item/non-existent")

        # Assert
        assert result is None


# ============================================================================
# ListProductsUseCase Tests
# ============================================================================


class TestListProductsUseCase:
    """Tests for ListProductsUseCase."""

    def test_execute_should_return_products_and_total(
        self, mock_product_repo, sample_product_entity
    ):
        """
        Given: Products exist in the repository
        When: execute() is called with default params
        Then: Should return a tuple of (list of products, total count)
        """
        # Arrange
        products = [sample_product_entity]
        mock_product_repo.get_all.return_value = (products, 1)
        use_case = ListProductsUseCase(mock_product_repo)

        # Act
        result_products, total = use_case.execute()

        # Assert
        assert result_products == products
        assert total == 1
        mock_product_repo.get_all.assert_called_once_with(
            limit=10, offset=0, sort_by=None, sort_order=None, filters=None
        )

    def test_execute_with_pagination_params_should_pass_to_repository(
        self, mock_product_repo
    ):
        """
        Given: Custom pagination and sorting parameters
        When: execute() is called
        Then: Should pass all parameters to the repository
        """
        # Arrange
        mock_product_repo.get_all.return_value = ([], 0)
        use_case = ListProductsUseCase(mock_product_repo)

        # Act
        use_case.execute(limit=5, offset=10, sort_by="title", sort_order="asc")

        # Assert
        mock_product_repo.get_all.assert_called_once_with(
            limit=5, offset=10, sort_by="title", sort_order="asc", filters=None
        )

    def test_execute_with_empty_repository_should_return_empty_list(
        self, mock_product_repo
    ):
        """
        Given: No products in the repository
        When: execute() is called
        Then: Should return empty list and zero total
        """
        # Arrange
        mock_product_repo.get_all.return_value = ([], 0)
        use_case = ListProductsUseCase(mock_product_repo)

        # Act
        result_products, total = use_case.execute()

        # Assert
        assert result_products == []
        assert total == 0


# ============================================================================
# UpdateProductUseCase Tests
# ============================================================================


class TestUpdateProductUseCase:
    """Tests for UpdateProductUseCase."""

    def test_execute_with_existing_product_should_return_updated_entity(
        self, mock_product_repo, sample_product_entity
    ):
        """
        Given: An existing product and updated data
        When: execute() is called
        Then: Should return the updated ProductEntity
        """
        # Arrange
        updated_entity = ProductEntity(
            id=1,
            url=sample_product_entity.url,
            title="iPhone 13 128GB - Updated",
            source_website_id=1,
            condition=ProductCondition.USED,
            is_available=True,
        )
        mock_product_repo.get_by_id.return_value = sample_product_entity
        mock_product_repo.update.return_value = updated_entity
        use_case = UpdateProductUseCase(mock_product_repo)

        update_data = ProductEntity(
            url=sample_product_entity.url,
            title="iPhone 13 128GB - Updated",
            source_website_id=1,
            condition=ProductCondition.USED,
            is_available=True,
        )

        # Act
        result = use_case.execute(1, update_data)

        # Assert
        assert result == updated_entity
        assert result.title == "iPhone 13 128GB - Updated"
        mock_product_repo.get_by_id.assert_called_once_with(1)
        mock_product_repo.update.assert_called_once()

    def test_execute_with_nonexistent_product_should_return_none(
        self, mock_product_repo, sample_product_entity
    ):
        """
        Given: A non-existent product ID
        When: execute() is called
        Then: Should return None without calling update
        """
        # Arrange
        mock_product_repo.get_by_id.return_value = None
        use_case = UpdateProductUseCase(mock_product_repo)

        # Act
        result = use_case.execute(999, sample_product_entity)

        # Assert
        assert result is None
        mock_product_repo.get_by_id.assert_called_once_with(999)
        mock_product_repo.update.assert_not_called()

    def test_execute_should_not_overwrite_protected_fields(
        self, mock_product_repo, sample_product_entity
    ):
        """
        Given: Update data that tries to change id and created_at
        When: execute() is called
        Then: Should ignore id and created_at fields
        """
        # Arrange
        original_created_at = sample_product_entity.created_at
        mock_product_repo.get_by_id.return_value = sample_product_entity
        mock_product_repo.update.return_value = sample_product_entity
        use_case = UpdateProductUseCase(mock_product_repo)

        update_data = ProductEntity(
            id=999,
            url=sample_product_entity.url,
            title="New Title",
            source_website_id=1,
            condition=ProductCondition.NEW,
            is_available=True,
            created_at=datetime(2000, 1, 1),
        )

        # Act
        use_case.execute(1, update_data)

        # Assert - the entity passed to repository.update should have original values
        call_args = mock_product_repo.update.call_args
        entity_passed = call_args[0][1]
        assert entity_passed.id != 999
        assert entity_passed.created_at == original_created_at


# ============================================================================
# DeleteProductUseCase Tests
# ============================================================================


class TestDeleteProductUseCase:
    """Tests for DeleteProductUseCase."""

    def test_execute_with_existing_product_should_return_true(self, mock_product_repo):
        """
        Given: An existing product ID
        When: execute() is called
        Then: Should delete and return True
        """
        # Arrange
        mock_product_repo.delete.return_value = True
        use_case = DeleteProductUseCase(mock_product_repo)

        # Act
        result = use_case.execute(1)

        # Assert
        assert result is True
        mock_product_repo.delete.assert_called_once_with(1)

    def test_execute_with_nonexistent_product_should_return_false(
        self, mock_product_repo
    ):
        """
        Given: A non-existent product ID
        When: execute() is called
        Then: Should return False
        """
        # Arrange
        mock_product_repo.delete.return_value = False
        use_case = DeleteProductUseCase(mock_product_repo)

        # Act
        result = use_case.execute(999)

        # Assert
        assert result is False
        mock_product_repo.delete.assert_called_once_with(999)
