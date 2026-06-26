"""Tests for inventory tools."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import purple_mcp.tools.inventory
from purple_mcp.libs.inventory.exceptions import (
    InventoryAPIError,
    InventoryAuthenticationError,
    InventoryNetworkError,
)
from purple_mcp.libs.inventory.field_presets import (
    InventoryFetchFieldsPreset,
    InventoryFetchFieldsPresetName,
)
from purple_mcp.libs.inventory.models import InventoryItem, InventoryResponse, PaginationInfo
from purple_mcp.tools.inventory import (
    _get_inventory_client,
    get_inventory_item,
    list_inventory_items,
    search_inventory_items,
)


@pytest.fixture
def _mock_inventory_item_with_known_set_fields() -> tuple[InventoryItem, set[str]]:
    """Create a mock inventory item with all STANDARD fields plus 3 from ALL.

    STANDARD fields (from InventoryFetchFieldsPreset.STANDARD):
    - id, idSecondary, name, category, resourceType, assetStatus, surfaces
    - lastActiveDt, infectionStatus, assetCriticality, activeCoverage, missingCoverage, riskFactors

    Additional fields from ALL (3 examples):
    - assetContactEmail, assetEnvironment, subCategory
    """
    # uses aliases where applicable
    params_dict = {
        # MINIMAL fields
        "id": "test-item-123",
        "idSecondary": ["secondary-id-1", "secondary-id-2"],
        "name": "Test Server",
        "category": "Server",
        "resourceType": "Windows Server",
        "assetStatus": None,  # null value should still be returned here , (SET EXPLICITLY)
        "surfaces": [],  # empty list should still be returned
        # Additional STANDARD fields
        "lastActiveDt": "2024-01-15T10:30:00Z",
        "infectionStatus": "Clean",
        "assetCriticality": "high",
        "activeCoverage": ["EDR", "Firewall"],
        "missingCoverage": ["DLP"],
        "riskFactors": ["Internet Facing", "Contains PII"],
        # 3 additional fields from ALL
        "assetContactEmail": "admin@example.com",
        "assetEnvironment": "Testing",
        "subCategory": "Database Server",
    }
    item = InventoryItem.model_validate(params_dict, by_alias=True)
    set_params = set(params_dict)
    return item, set_params


@pytest.fixture
def mock_inventory_item(
    _mock_inventory_item_with_known_set_fields: tuple[InventoryItem, set[str]],
) -> InventoryItem:
    """Return the InventoryItem from the combined fixture."""
    return _mock_inventory_item_with_known_set_fields[0]


@pytest.fixture
def known_set_fields(
    _mock_inventory_item_with_known_set_fields: tuple[InventoryItem, set[str]],
) -> set[str]:
    """Return the set of field names from the combined fixture."""
    return _mock_inventory_item_with_known_set_fields[1]


@pytest.fixture
def mock_inventory_client() -> MagicMock:
    """Create a mock inventory client with async context manager support.

    Returns a configured MagicMock that:
    - Supports async context manager protocol (__aenter__, __aexit__)
    - Has no pre-configured methods (tests must configure as needed)
    - Configure specific methods on a per-test basis (e.g., get_inventory_item, list_inventory, search_inventory)
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestGetInventoryItem:
    """Test get_inventory_item function."""

    @pytest.mark.asyncio
    async def test_get_inventory_item_found(
        self,
        mock_inventory_item: InventoryItem,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test getting an inventory item that exists."""
        mock_inventory_client.get_inventory_item = AsyncMock(return_value=mock_inventory_item)

        assert mock_inventory_item.id is not None
        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await get_inventory_item(mock_inventory_item.id)

        # Parse JSON result - uses camelCase aliases with by_alias=True
        result_data = json.loads(result)
        assert result_data["id"] == mock_inventory_item.id
        assert result_data["name"] == mock_inventory_item.name
        # resourceType is serialized as camelCase alias with by_alias=True
        assert result_data["resourceType"] == mock_inventory_item.resource_type

    @pytest.mark.asyncio
    async def test_get_inventory_item_not_found(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test getting an inventory item that doesn't exist."""
        mock_inventory_client.get_inventory_item = AsyncMock(return_value=None)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

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
    async def test_get_inventory_item_api_error(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that API errors are preserved."""
        mock_inventory_client.get_inventory_item = AsyncMock(
            side_effect=InventoryAPIError("API error occurred")
        )

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        with pytest.raises(InventoryAPIError) as exc_info:
            await get_inventory_item("test-123")

        assert "API error occurred" in str(exc_info.value)

    @pytest.mark.parametrize(
        "fetch_fields", [preset.name for preset in InventoryFetchFieldsPreset]
    )
    @pytest.mark.asyncio
    async def test_get_inventory_item_with_minimal_fetch_fields(
        self,
        mock_inventory_item: InventoryItem,
        known_set_fields: set[str],
        fetch_fields: InventoryFetchFieldsPresetName,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test getting an inventory item with MINIMAL fetch_fields preset."""
        mock_inventory_client.get_inventory_item = AsyncMock(return_value=mock_inventory_item)

        assert mock_inventory_item.id is not None
        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        fields_in_standard_but_not_minimal = set(InventoryFetchFieldsPreset.STANDARD.value) - set(
            InventoryFetchFieldsPreset.MINIMAL.value
        )

        result = await get_inventory_item(mock_inventory_item.id, fetch_fields=fetch_fields)

        result_data = json.loads(result)

        # Check we're getting all expected fields:
        for field in InventoryFetchFieldsPreset[fetch_fields].value:
            if field in known_set_fields:
                assert field in result_data, f"{fetch_fields} field '{field}' not in result"
            else:
                assert field not in result_data, f"Unset field '{field}' should not be in result"

        if fetch_fields == InventoryFetchFieldsPreset.MINIMAL.name:
            # For minimal set, None of the STANDARD_EXTRA fields should be present
            for field in fields_in_standard_but_not_minimal:
                assert field not in result_data, (
                    f"STANDARD_EXTRA field '{field}' should not be in MINIMAL result"
                )

    @pytest.mark.asyncio
    async def test_get_inventory_item_with_custom_fetch_fields_list(
        self,
        mock_inventory_item: InventoryItem,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test getting an inventory item with custom field list."""
        mock_inventory_client.get_inventory_item = AsyncMock(return_value=mock_inventory_item)

        # 3 fields that are set on the mock example, +one that is UNSET
        unset_field = "osFamily"
        assert unset_field not in mock_inventory_item.model_fields_set
        set_fields = ["id", "name", "assetContactEmail"]
        assert "asset_contact_email" in mock_inventory_item.model_fields_set
        assert "os_family" not in mock_inventory_item.model_fields_set
        custom_fields_list = [*set_fields, unset_field]

        assert mock_inventory_item.id is not None
        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await get_inventory_item(
            mock_inventory_item.id,
            fetch_fields=custom_fields_list,
        )

        result_data = json.loads(result)
        assert "id" in result_data
        assert "name" in result_data
        assert "assetContactEmail" in result_data
        assert result_data["id"] == mock_inventory_item.id
        assert result_data["name"] == mock_inventory_item.name
        assert result_data["assetContactEmail"] == mock_inventory_item.asset_contact_email
        # Fields not requested should not be included
        assert "resourceType" not in result_data
        assert unset_field not in result_data

    @pytest.mark.asyncio
    async def test_get_inventory_item_with_invalid_fetch_fields(self) -> None:
        """Test that invalid fetch_fields raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await get_inventory_item("test-123", fetch_fields=["invalid_field"])

        assert "Invalid field names" in str(exc_info.value)
        assert "invalid_field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_inventory_item_with_invalid_fetch_fields_preset(self) -> None:
        """Test that invalid fetch_fields raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            # type-ignore here for intentionally bad value:
            await get_inventory_item("test-123", fetch_fields="BADPRESET")  # type: ignore[arg-type]

        assert "Invalid preset name" in str(exc_info.value)
        assert "Valid presets: MINIMAL, STANDARD, ALL" in str(exc_info.value)


class TestListInventoryItems:
    """Test list_inventory_items function."""

    @pytest.mark.asyncio
    async def test_list_inventory_items_default_params(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test listing inventory items with default parameters."""
        mock_response = InventoryResponse(
            data=[
                InventoryItem(id="item-1", name="Item 1"),
                InventoryItem(id="item-2", name="Item 2"),
            ],
            pagination=PaginationInfo(totalCount=2, limit=50, skip=0),
        )

        mock_inventory_client.list_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await list_inventory_items()

        # Parse and verify result - uses camelCase aliases with by_alias=True
        result_data = json.loads(result)
        assert len(result_data["data"]) == 2
        assert result_data["data"][0]["id"] == "item-1"
        assert result_data["pagination"]["totalCount"] == 2

    @pytest.mark.asyncio
    async def test_list_inventory_items_with_pagination(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test listing inventory items with custom pagination."""
        mock_response = InventoryResponse(
            data=[InventoryItem(id="item-1")],
            pagination=PaginationInfo(totalCount=100, limit=10, skip=20),
        )

        mock_inventory_client.list_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        await list_inventory_items(limit=10, skip=20)

        # Verify client was called with correct params (no fetch_fields parameter)
        mock_inventory_client.list_inventory.assert_called_once_with(
            limit=10, skip=20, surface=None
        )

    @pytest.mark.asyncio
    async def test_list_inventory_items_with_surface(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test listing inventory items with surface filter."""
        from purple_mcp.libs.inventory.models import Surface

        mock_response = InventoryResponse(data=[], pagination=None)

        mock_inventory_client.list_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        await list_inventory_items(surface="ENDPOINT")

        # Verify client was called with Surface enum
        call_args = mock_inventory_client.list_inventory.call_args
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
        self,
        exception_class: type[Exception],
        error_message: str,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that client errors are preserved."""
        mock_inventory_client.list_inventory = AsyncMock(
            side_effect=exception_class(error_message)
        )

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        with pytest.raises(exception_class) as exc_info:
            await list_inventory_items()

        assert error_message in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_inventory_items_with_standard_fetch_fields(
        self,
        mock_inventory_item: InventoryItem,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test listing inventory items with STANDARD fetch_fields preset."""
        mock_response = InventoryResponse(
            data=[mock_inventory_item],
            pagination=PaginationInfo(totalCount=1, limit=50, skip=0),
        )

        mock_inventory_client.list_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await list_inventory_items(fetch_fields="STANDARD")

        result_data = json.loads(result)
        assert len(result_data["data"]) == 1
        # All STANDARD fields should be present
        for field in InventoryFetchFieldsPreset.STANDARD.value:
            assert field in result_data["data"][0], f"STANDARD field '{field}' not in result"
        # Fields from ALL but not STANDARD should not be included
        all_preset_set = set(InventoryFetchFieldsPreset.ALL.value)
        standard_preset_set = set(InventoryFetchFieldsPreset.STANDARD.value)
        extra_fields = all_preset_set - standard_preset_set
        for field in extra_fields:
            assert field not in result_data["data"][0], (
                f"Non-STANDARD field '{field}' should not be in STANDARD result"
            )

    @pytest.mark.asyncio
    async def test_list_inventory_items_with_all_fetch_fields(
        self,
        mock_inventory_item: InventoryItem,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test listing inventory items with ALL fetch_fields preset."""
        mock_response = InventoryResponse(
            data=[mock_inventory_item],
            pagination=None,
        )

        mock_inventory_client.list_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await list_inventory_items(fetch_fields="ALL")

        result_data = json.loads(result)
        assert len(result_data["data"]) == 1
        # All fields from ALL preset should be present (at least those with values in fixture)
        assert "id" in result_data["data"][0]
        # Verify we have some ALL-only fields
        assert "assetContactEmail" in result_data["data"][0]
        assert "assetEnvironment" in result_data["data"][0]
        assert "subCategory" in result_data["data"][0]

    @pytest.mark.asyncio
    async def test_list_inventory_items_with_empty_fetch_fields_raises_error(self) -> None:
        """Test that empty fetch_fields raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await list_inventory_items(fetch_fields=[])

        assert "cannot be empty" in str(exc_info.value).lower()


class TestSearchInventoryItems:
    """Test search_inventory_items function."""

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_filters(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test searching inventory items with filters."""
        filters_json = '{"resourceType": ["Windows Server"]}'
        mock_response = InventoryResponse(
            data=[InventoryItem(id="server-1", resourceType="Windows Server")],
            pagination=PaginationInfo(totalCount=1, limit=50, skip=0),
        )

        mock_inventory_client.search_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await search_inventory_items(filters=filters_json)

        # Verify client was called with parsed filters
        call_args = mock_inventory_client.search_inventory.call_args
        assert call_args[1]["filters"] == {"resourceType": ["Windows Server"]}

        # Verify result - uses camelCase aliases with by_alias=True
        result_data = json.loads(result)
        assert len(result_data["data"]) == 1
        assert result_data["data"][0]["resourceType"] == "Windows Server"

    @pytest.mark.asyncio
    async def test_search_inventory_items_no_filters(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test searching inventory items without filters."""
        mock_response = InventoryResponse(data=[], pagination=None)

        mock_inventory_client.search_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        await search_inventory_items()

        # Verify client was called with empty filters
        call_args = mock_inventory_client.search_inventory.call_args
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
    async def test_search_inventory_items_with_complex_filters(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test searching with complex filter combinations."""
        filters_json = json.dumps(
            {
                "name__contains": ["test"],
                "lastActiveDt__between": {"from": "2024-01-01", "to": "2024-12-31"},
                "assetStatus": ["Active"],
            }
        )

        mock_response = InventoryResponse(data=[], pagination=None)

        mock_inventory_client.search_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        await search_inventory_items(filters=filters_json)

        # Verify filters were correctly parsed and passed
        call_args = mock_inventory_client.search_inventory.call_args
        filters = call_args[1]["filters"]
        assert "name__contains" in filters
        assert "lastActiveDt__between" in filters
        assert "assetStatus" in filters

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_pagination(
        self, mock_inventory_client: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test searching with custom pagination parameters."""
        mock_response = InventoryResponse(data=[], pagination=None)

        mock_inventory_client.search_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        await search_inventory_items(limit=100, skip=50)

        # Verify pagination params were passed
        call_args = mock_inventory_client.search_inventory.call_args
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
        self,
        exception_class: type[Exception],
        error_message: str,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that client errors are preserved."""
        mock_inventory_client.search_inventory = AsyncMock(
            side_effect=exception_class(error_message)
        )

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        with pytest.raises(exception_class) as exc_info:
            await search_inventory_items()

        assert error_message in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_minimal_fetch_fields(
        self,
        mock_inventory_item: InventoryItem,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test searching inventory items with MINIMAL fetch_fields preset."""
        filters_json = '{"resourceType": ["Windows Server"]}'
        mock_response = InventoryResponse(
            data=[mock_inventory_item],
            pagination=PaginationInfo(totalCount=1, limit=50, skip=0),
        )

        mock_inventory_client.search_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )
        fields_in_standard_but_not_minimal = set(InventoryFetchFieldsPreset.STANDARD.value) - set(
            InventoryFetchFieldsPreset.MINIMAL.value
        )

        result = await search_inventory_items(filters=filters_json, fetch_fields="MINIMAL")

        result_data = json.loads(result)
        assert len(result_data["data"]) == 1
        # All MINIMAL fields should be present
        for field in InventoryFetchFieldsPreset.MINIMAL.value:
            assert field in result_data["data"][0], f"MINIMAL field '{field}' not in result"
        # None of the STANDARD_EXTRA fields should be present
        for field in fields_in_standard_but_not_minimal:
            assert field not in result_data["data"][0], (
                f"STANDARD_EXTRA field '{field}' should not be in MINIMAL result"
            )

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_custom_fetch_fields_list(
        self,
        mock_inventory_item: InventoryItem,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test searching inventory items with custom field list."""
        mock_response = InventoryResponse(
            data=[mock_inventory_item],
            pagination=PaginationInfo(totalCount=1, limit=50, skip=0),
        )

        mock_inventory_client.search_inventory = AsyncMock(return_value=mock_response)

        fetch_fields = ["id", "name", "category", "assetEnvironment"]
        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await search_inventory_items(fetch_fields=fetch_fields)

        result_data = json.loads(result)
        for field in fetch_fields:
            assert field in result_data["data"][0]

        assert result_data["data"][0]["id"] == mock_inventory_item.id
        assert result_data["data"][0]["name"] == mock_inventory_item.name
        assert result_data["data"][0]["category"] == mock_inventory_item.category
        assert result_data["data"][0]["assetEnvironment"] == mock_inventory_item.asset_environment
        # Fields not requested should not be included
        assert "assetContactEmail" not in result_data["data"][0]

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_all_fetch_fields(
        self,
        mock_inventory_item: InventoryItem,
        mock_inventory_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test searching inventory items with ALL fetch_fields preset."""
        mock_response = InventoryResponse(
            data=[mock_inventory_item],
            pagination=None,
        )

        mock_inventory_client.search_inventory = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(
            purple_mcp.tools.inventory,
            _get_inventory_client.__name__,
            lambda: mock_inventory_client,
        )

        result = await search_inventory_items(fetch_fields="ALL")

        result_data = json.loads(result)
        assert len(result_data["data"]) == 1
        # All fields from ALL preset should be present (at least those with values in fixture)
        assert "id" in result_data["data"][0]
        # Verify we have some ALL-only fields
        assert "assetContactEmail" in result_data["data"][0]
        assert "assetEnvironment" in result_data["data"][0]
        assert "subCategory" in result_data["data"][0]

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_empty_fetch_fields_raises_error(self) -> None:
        """Test that empty fetch_fields raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await search_inventory_items(fetch_fields=[])

        assert "cannot be empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_inventory_items_with_invalid_fetch_fields(self) -> None:
        """Test that invalid fetch_fields raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await search_inventory_items(fetch_fields=["invalid_field", "another_invalid"])

        assert "Invalid field names" in str(exc_info.value)
        assert "invalid_field" in str(exc_info.value)


class TestGetInventoryClient:
    """Test _get_inventory_client helper function."""

    @pytest.mark.asyncio
    async def test_get_inventory_client_settings_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that settings errors are properly handled."""
        mock_get_settings = MagicMock(side_effect=RuntimeError("Settings not configured"))
        monkeypatch.setattr(purple_mcp.tools.inventory, "get_settings", mock_get_settings)

        with pytest.raises(RuntimeError) as exc_info:
            _get_inventory_client()

        assert "Settings not initialized" in str(exc_info.value)
