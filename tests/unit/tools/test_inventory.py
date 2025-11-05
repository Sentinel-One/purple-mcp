"""Tests for inventory tools."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from purple_mcp.libs.inventory.exceptions import (
    InventoryAPIError,
    InventoryAuthenticationError,
    InventoryNetworkError,
)
from purple_mcp.libs.inventory.models import InventoryItem, InventoryResponse, PaginationInfo
from purple_mcp.tools.inventory import (
    get_inventory_item,
    list_inventory_items,
    search_inventory_items,
)


class TestGetInventoryItem:
    """Test get_inventory_item function."""

    @pytest.mark.asyncio
    async def test_get_inventory_item_found(self) -> None:
        """Test getting an inventory item that exists."""
        mock_item = InventoryItem(
            id="test-123",
            name="Test Server",
            resource_type="Windows Server",
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_inventory_item = AsyncMock(return_value=mock_item)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            result = await get_inventory_item("test-123")

        # Parse JSON result - uses snake_case by default
        result_data = json.loads(result)
        assert result_data["id"] == "test-123"
        assert result_data["name"] == "Test Server"
        # resource_type is serialized as snake_case by default
        assert result_data["resource_type"] == "Windows Server"

    @pytest.mark.asyncio
    async def test_get_inventory_item_not_found(self) -> None:
        """Test getting an inventory item that doesn't exist."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_inventory_item = AsyncMock(return_value=None)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            result = await get_inventory_item("nonexistent-id")

        # Should return JSON null
        assert result == json.dumps(None, indent=2)

    @pytest.mark.parametrize(
        "item_id",
        [
            pytest.param("", id="empty-id"),
            pytest.param("   ", id="whitespace-only-id"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_inventory_item_invalid_id(self, item_id: str) -> None:
        """Test that invalid item_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await get_inventory_item(item_id)

        assert "cannot be empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_inventory_item_api_error(self) -> None:
        """Test that API errors are preserved."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_inventory_item = AsyncMock(
            side_effect=InventoryAPIError("API error occurred")
        )

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            with pytest.raises(InventoryAPIError) as exc_info:
                await get_inventory_item("test-123")

            assert "API error occurred" in str(exc_info.value)


class TestListInventoryItems:
    """Test list_inventory_items function."""

    @pytest.mark.asyncio
    async def test_list_inventory_items_default_params(self) -> None:
        """Test listing inventory items with default parameters."""
        mock_response = InventoryResponse(
            data=[
                InventoryItem(id="item-1", name="Item 1"),
                InventoryItem(id="item-2", name="Item 2"),
            ],
            pagination=PaginationInfo(total_count=2, limit=50, skip=0),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_inventory = AsyncMock(return_value=mock_response)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            result = await list_inventory_items()

        # Parse and verify result - uses snake_case by default
        result_data = json.loads(result)
        assert len(result_data["data"]) == 2
        assert result_data["data"][0]["id"] == "item-1"
        assert result_data["pagination"]["total_count"] == 2

    @pytest.mark.asyncio
    async def test_list_inventory_items_with_pagination(self) -> None:
        """Test listing inventory items with custom pagination."""
        mock_response = InventoryResponse(
            data=[InventoryItem(id="item-1")],
            pagination=PaginationInfo(total_count=100, limit=10, skip=20),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_inventory = AsyncMock(return_value=mock_response)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            await list_inventory_items(limit=10, skip=20)

        # Verify client was called with correct params
        mock_client.list_inventory.assert_called_once_with(limit=10, skip=20, surface=None)

    @pytest.mark.asyncio
    async def test_list_inventory_items_with_surface(self) -> None:
        """Test listing inventory items with surface filter."""
        from purple_mcp.libs.inventory.models import Surface

        mock_response = InventoryResponse(data=[], pagination=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_inventory = AsyncMock(return_value=mock_response)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            await list_inventory_items(surface="ENDPOINT")

        # Verify client was called with Surface enum
        call_args = mock_client.list_inventory.call_args
        assert call_args[1]["surface"] == Surface.ENDPOINT

    @pytest.mark.parametrize(
        ("kwargs", "expected_error"),
        [
            pytest.param({"limit": 0}, "limit must be between", id="invalid-limit-zero"),
            pytest.param({"limit": 2000}, "limit must be between", id="limit-exceeds-maximum"),
            pytest.param({"skip": -1}, "skip must be non-negative", id="negative-skip"),
            pytest.param(
                {"surface": "INVALID_SURFACE"}, "surface must be one of", id="invalid-surface"
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_list_inventory_items_validation_errors(
        self, kwargs: dict[str, Any], expected_error: str
    ) -> None:
        """Test that invalid parameters raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await list_inventory_items(**kwargs)

        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        ("exception_class", "error_message"),
        [
            pytest.param(
                InventoryAuthenticationError,
                "Authentication failed",
                id="authentication-error",
            ),
            pytest.param(InventoryNetworkError, "Network timeout", id="network-error"),
            pytest.param(InventoryAPIError, "API error occurred", id="api-error"),
        ],
    )
    @pytest.mark.asyncio
    async def test_list_inventory_items_error_preservation(
        self, exception_class: type[Exception], error_message: str
    ) -> None:
        """Test that client errors are preserved."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_inventory = AsyncMock(side_effect=exception_class(error_message))

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            with pytest.raises(exception_class) as exc_info:
                await list_inventory_items()

            assert error_message in str(exc_info.value)


class TestSearchInventoryItems:
    """Test search_inventory_items function."""

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_filters(self) -> None:
        """Test searching inventory items with filters."""
        filters_json = '{"resourceType": ["Windows Server"]}'
        mock_response = InventoryResponse(
            data=[InventoryItem(id="server-1", resource_type="Windows Server")],
            pagination=PaginationInfo(total_count=1, limit=50, skip=0),
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search_inventory = AsyncMock(return_value=mock_response)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            result = await search_inventory_items(filters=filters_json)

        # Verify client was called with parsed filters
        call_args = mock_client.search_inventory.call_args
        assert call_args[1]["filters"] == {"resourceType": ["Windows Server"]}

        # Verify result - uses snake_case by default
        result_data = json.loads(result)
        assert len(result_data["data"]) == 1
        assert result_data["data"][0]["resource_type"] == "Windows Server"

    @pytest.mark.asyncio
    async def test_search_inventory_items_no_filters(self) -> None:
        """Test searching inventory items without filters."""
        mock_response = InventoryResponse(data=[], pagination=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search_inventory = AsyncMock(return_value=mock_response)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            await search_inventory_items()

        # Verify client was called with empty filters
        call_args = mock_client.search_inventory.call_args
        assert call_args[1]["filters"] == {}

    @pytest.mark.parametrize(
        ("filters", "expected_error"),
        [
            pytest.param('{"invalid json"}', "Invalid JSON", id="invalid-json"),
            pytest.param('["not", "a", "dict"]', "must be a dictionary", id="non-dict-filters"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_inventory_items_invalid_filters(
        self, filters: str, expected_error: str
    ) -> None:
        """Test that invalid filters raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await search_inventory_items(filters=filters)

        assert expected_error in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_complex_filters(self) -> None:
        """Test searching with complex filter combinations."""
        filters_json = json.dumps(
            {
                "name__contains": ["prod"],
                "lastActiveDt__between": {"from": "2024-01-01", "to": "2024-12-31"},
                "assetStatus": ["Active"],
            }
        )

        mock_response = InventoryResponse(data=[], pagination=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search_inventory = AsyncMock(return_value=mock_response)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            await search_inventory_items(filters=filters_json)

        # Verify filters were correctly parsed and passed
        call_args = mock_client.search_inventory.call_args
        filters = call_args[1]["filters"]
        assert "name__contains" in filters
        assert "lastActiveDt__between" in filters
        assert "assetStatus" in filters

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_pagination(self) -> None:
        """Test searching with custom pagination parameters."""
        mock_response = InventoryResponse(data=[], pagination=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search_inventory = AsyncMock(return_value=mock_response)

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            await search_inventory_items(limit=100, skip=50)

        # Verify pagination params were passed
        call_args = mock_client.search_inventory.call_args
        assert call_args[1]["limit"] == 100
        assert call_args[1]["skip"] == 50

    @pytest.mark.parametrize(
        ("exception_class", "error_message"),
        [
            pytest.param(
                InventoryAuthenticationError,
                "Authentication failed",
                id="authentication-error",
            ),
            pytest.param(InventoryNetworkError, "Network timeout", id="network-error"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_inventory_items_error_preservation(
        self, exception_class: type[Exception], error_message: str
    ) -> None:
        """Test that client errors are preserved."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.search_inventory = AsyncMock(side_effect=exception_class(error_message))

        with patch("purple_mcp.tools.inventory._get_inventory_client", return_value=mock_client):
            with pytest.raises(exception_class) as exc_info:
                await search_inventory_items()

            assert error_message in str(exc_info.value)


class TestGetInventoryClient:
    """Test _get_inventory_client helper function."""

    @pytest.mark.asyncio
    async def test_get_inventory_client_settings_error(self) -> None:
        """Test that settings errors are properly handled."""
        with patch(
            "purple_mcp.tools.inventory.get_settings",
            side_effect=RuntimeError("Settings not configured"),
        ):
            from purple_mcp.tools.inventory import _get_inventory_client

            with pytest.raises(RuntimeError) as exc_info:
                _get_inventory_client()

            assert "Settings not initialized" in str(exc_info.value)
