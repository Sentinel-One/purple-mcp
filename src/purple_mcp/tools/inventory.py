"""Tools for interacting with the Unified Asset Inventory system."""

import json
import logging
from collections.abc import Iterable
from textwrap import dedent
from typing import Final, Literal

from purple_mcp.config import get_settings, validate_request_credentials
from purple_mcp.libs.inventory import (
    InventoryAPIError,
    InventoryAuthenticationError,
    InventoryClient,
    InventoryClientError,
    InventoryConfig,
    InventoryFetchFieldsPreset,
    InventoryFetchFieldsPresetName,
    InventoryNetworkError,
    Surface,
)
from purple_mcp.libs.inventory.models import InventoryItem
from purple_mcp.type_defs import JsonDict

logger = logging.getLogger(__name__)

# DoS protection constants
MAX_LIMIT: Final = 1000

# Tool description constants
GET_INVENTORY_ITEM_DESCRIPTION: Final[str] = dedent(
    """
    Get detailed information about a specific managed asset in SentinelOne by ID.

    Use this tool to retrieve information about SentinelOne managed assets such as
    computers, servers, workstations, cloud resources, and network devices.

    Args:
        item_id: The unique identifier of the inventory item.
        fetch_fields: Field filtering. Either:
                      - Preset name: "MINIMAL", "STANDARD", or "ALL" (default: "ALL")
                        * MINIMAL: 7 core fields (id, name, category, etc.)
                        * STANDARD: 13 fields (MINIMAL + operational context)
                        * ALL: All available fields (~200+ fields)
                      - List of specific field names in camelCase:
                        Examples: ["id", "name", "resourceType"]
                                  ["id", "osVersion", "ipAddress", "lastActiveDt"]
                      Defaults to "ALL" to return complete asset information.

    Returns:
        JSON string containing the requested fields (keys use camelCase format).
        Fields without values are excluded from the output.

    Raises:
        ValueError: If item_id is invalid or empty, or fetch_fields is invalid.
        InventoryAuthenticationError: If authentication fails.
        InventoryNetworkError: If network operation fails.
        InventoryAPIError: If the API returns an error.
        InventoryClientError: For other client-level errors.
    """
).strip()

LIST_INVENTORY_ITEMS_DESCRIPTION: Final[str] = dedent(
    """
    List managed assets in SentinelOne with pagination and optional filtering.

    Use this tool to browse SentinelOne managed assets including computers, servers,
    workstations, cloud resources, and network-discovered devices.

    Args:
        limit: Number of items to retrieve (1-1000, default: 50).
        skip: Number of items to skip for pagination (default: 0).
        surface: Optional surface filter:
                 - "ENDPOINT": Endpoint assets (agents, workstations, servers, computers)
                 - "CLOUD": Cloud resources (AWS, Azure, GCP)
                 - "IDENTITY": Identity entities (AD, Entra ID)
                 - "NETWORK_DISCOVERY": Network-discovered devices (Ranger)
        fetch_fields: Field filtering. Either:
                      - Preset name: "MINIMAL", "STANDARD", or "ALL" (default: "MINIMAL")
                        * MINIMAL: 7 core fields (id, name, category, etc.) - fastest
                        * STANDARD: 13 fields (MINIMAL + operational context)
                        * ALL: All available fields (~200+ fields) - slowest
                      - List of specific field names in camelCase:
                        Examples: ["id", "name", "category"]
                                  ["id", "resourceType", "assetStatus", "lastActiveDt"]
                      Use fetch_fields="ALL" on a single item to discover all field names.
                      Defaults to "MINIMAL" for optimal performance with list operations.

    Returns:
        JSON string with paginated inventory items containing only requested fields.
        Field keys use camelCase format.
        Fields without values are excluded from the output. Includes pagination metadata.

    Raises:
        ValueError: If parameters are invalid, or fetch_fields is invalid.
        InventoryAuthenticationError: If authentication fails.
        InventoryNetworkError: If network operation fails.
        InventoryAPIError: If the API returns an error.
        InventoryClientError: For other client-level errors.
    """
).strip()

SEARCH_INVENTORY_ITEMS_DESCRIPTION: Final[str] = dedent(
    """
    Search for managed assets in SentinelOne using REST API filters.

    Use this tool to find specific SentinelOne managed assets such as computers, servers,
    workstations, cloud resources, and network devices by various criteria (name, type,
    status, tags, etc.). Multiple filters are combined with AND logic.

    Note: For surface-specific filtering (ENDPOINT, CLOUD, IDENTITY, NETWORK_DISCOVERY),
    use the list_inventory_items tool instead, which supports surface filtering via GET.

    Args:
        filters: JSON string containing filter dictionary (optional, default: {}).
                 Use REST API filter format with field names in camelCase.

                 Standard Filters (exact match - matches ANY value in list):
                 - {"resourceType": ["Windows Server", "Linux Server"]}
                 - {"assetStatus": ["Active", "Inactive"]}
                 - {"category": ["Server", "Workstation"]}
                 - {"infectionStatus": ["Infected", "Healthy"]}

                 Contains Filters (partial match - case-insensitive):
                 - {"name__contains": ["dev", "test"]}
                 - {"cloudProviderAccountName__contains": ["testing"]}
                 - {"osName__contains": ["Windows", "Ubuntu"]}

                 Range Filters (date ranges - use ISO date strings or millisecond timestamps):
                 - {"lastActiveDt__between": {"from": "2024-01-01", "to": "2024-12-31"}}
                 - {"lastActiveDt__between": {"from": 1704067200000, "to": 1735689599000}}

                 IMPORTANT: All datetimes in the Inventory API are in UTC timezone.
                 For timestamp-based date filters, you can use the iso_to_unix_timestamp tool
                 to convert ISO 8601 datetime strings to UNIX timestamps in milliseconds (UTC).

                 The iso_to_unix_timestamp tool handles timezone conversion automatically.
                 Provide datetimes in the user's preferred timezone (e.g., "2024-01-01T00:00:00-05:00" for Eastern Time)
                 and the tool will convert to UTC milliseconds for the API.

                 Example workflow for timestamp filters:
                 1. Call iso_to_unix_timestamp("2024-01-01T00:00:00-05:00") -> returns "1704085200000" (UTC)
                 2. Use in filter: {"lastActiveDt__between": {"from": 1704085200000, "to": 1735693199000}}

                 ID Filters (exact ID matches):
                 - {"id__in": ["uuid1", "uuid2", "uuid3"]}

                 Negation Filters (exclude values):
                 - {"assetStatus__nin": ["Decommissioned"]}
                 - {"resourceType__nin": ["Unknown"]}

                 Combining Filters (AND logic - all must match):
                 - {"resourceType": ["Windows Server"], "assetStatus": ["Active"], "name__contains": ["test"]}

                 Common Examples:
                 - Find testing servers: {"name__contains": ["test"], "resourceType": ["Windows Server", "Linux Server"]}
                 - Find active AWS instances: {"cloudProvider": ["AWS"], "assetStatus": ["Active"]}
                 - Find recently active endpoints: {"lastActiveDt__between": {"from": "2024-12-01", "to": "2024-12-31"}}

        limit: Number of items to retrieve (1-1000, default: 50).
        skip: Number of items to skip for pagination (default: 0).
        fetch_fields: Field filtering. Either:
                      - Preset name: "MINIMAL", "STANDARD", or "ALL" (default: "MINIMAL")
                        * MINIMAL: 7 core fields (id, name, category, etc.) - fastest
                        * STANDARD: 13 fields (MINIMAL + operational context)
                        * ALL: All available fields (~200+ fields) - slowest
                      - List of specific field names in camelCase:
                        Examples: ["id", "name", "resourceType", "assetStatus"]
                                  ["id", "category", "osVersion", "ipAddress"]
                      Use fetch_fields="ALL" on a single item to discover all field names.
                      Defaults to "MINIMAL" for optimal performance with search operations.

    Returns:
        JSON string with filtered inventory items containing only requested fields.
        Field keys use camelCase format.
        Fields without values are excluded from the output. Includes pagination metadata.
        Returns empty list if no matches found.

    Raises:
        ValueError: If filters JSON is invalid, parameters are out of range, or fetch_fields is invalid.
        InventoryAuthenticationError: If authentication fails.
        InventoryNetworkError: If network operation fails.
        InventoryAPIError: If the API returns an error.
        InventoryClientError: For other client-level errors.
    """
).strip()


def _parse_fetch_fields(
    fetch_fields: Literal["MINIMAL", "STANDARD", "ALL"] | Iterable[str],
) -> set[str]:
    """Parse and validate fetch_fields parameter.

    Args:
        fetch_fields: Either a preset name (MINIMAL/STANDARD/ALL) or an iterable of field names
                      in camelCase format (e.g., ["id", "resourceType", "assetStatus"]).

    Returns:
        Set of validated field names (camelCase aliases) that can be passed to
        _map_aliases_to_field_names() for conversion to Pydantic field names.

    Raises:
        ValueError: If fetch_fields is not a string/iterable, is empty, contains non-strings,
                    contains invalid field names not in ALL preset, or preset name is invalid.
    """
    # Handle string preset names
    if isinstance(fetch_fields, str):
        preset_name = fetch_fields.upper()
        try:
            preset = InventoryFetchFieldsPreset[preset_name]
            return set(preset.value)
        except KeyError:
            valid_names = [p.name for p in InventoryFetchFieldsPreset]
            raise ValueError(
                f"Invalid preset name '{fetch_fields}'. Valid presets: {', '.join(valid_names)}"
            ) from None

    fetch_fields = set(fetch_fields)
    if len(fetch_fields) == 0:
        raise ValueError("fetch_fields iterable cannot be empty")

    # Validate all fields exist in ALL preset
    all_fields_set = set(InventoryFetchFieldsPreset.ALL.value)
    invalid_fields = [f for f in fetch_fields if f not in all_fields_set]
    if len(invalid_fields) > 0:
        raise ValueError(
            f"Invalid field names: {invalid_fields}. Use 'ALL' preset to see all available fields."
        )

    return fetch_fields


def _get_inventory_client() -> InventoryClient:
    """Get a configured InventoryClient instance.

    Returns:
        Configured InventoryClient instance.

    Raises:
        RuntimeError: If settings are not properly configured.
    """
    try:
        settings = get_settings()
    except Exception as e:
        raise RuntimeError(
            f"Settings not initialized. Please check your environment configuration. Error: {e}"
        ) from e

    # Validate credentials are available
    validate_request_credentials(settings)

    # After validation, credentials are guaranteed to be non-None
    assert settings.sentinelone_console_base_url is not None
    assert settings.graphql_service_token is not None

    config = InventoryConfig(
        base_url=settings.sentinelone_console_base_url,
        api_endpoint=settings.sentinelone_inventory_restapi_endpoint,
        api_token=settings.graphql_service_token,
    )

    return InventoryClient(config)


async def get_inventory_item(
    item_id: str,
    fetch_fields: InventoryFetchFieldsPresetName | list[str] = InventoryFetchFieldsPreset.ALL.name,
) -> str:
    """Get detailed information about a specific inventory item by ID.

    Args:
        item_id: The unique identifier of the inventory item.
        fetch_fields: Field filtering (default: "ALL"). Either:
                      - Preset name: "MINIMAL", "STANDARD", or "ALL"
                      - List of specific field names in camelCase (e.g., ["id", "resourceType"])
                      Field names must match those in InventoryFetchFieldsPreset.ALL.
                      **Note: type-hint is `list[str]` because `Iterable[str]` causes issues with FastMCP wrapping.**

    Returns:
        JSON string containing only the requested fields in camelCase format.
        Fields without values are excluded (exclude_unset=True).

    Raises:
        ValueError: If item_id is empty, if fetch_fields is empty, if preset name is invalid,
                    or if custom field names are not in ALL preset.
        InventoryAuthenticationError: If authentication fails.
        InventoryNetworkError: If network operation fails.
        InventoryAPIError: If the API returns an error.
        InventoryClientError: For other client-level errors.
    """
    try:
        if not item_id or not item_id.strip():
            raise ValueError("item_id cannot be empty")

        # Parse and validate fetch_fields
        validated_aliases = _parse_fetch_fields(fetch_fields)
        # Map aliases to actual field names for Pydantic include parameter
        field_names = InventoryItem._map_aliases_to_field_names(validated_aliases)

        client = _get_inventory_client()
        async with client:
            item = await client.get_inventory_item(item_id)

            if item is None:
                return json.dumps(None, indent=2)

            # Apply field filtering using Pydantic with aliases
            # include parameter needs actual field names, by_alias=True outputs aliases
            return item.model_dump_json_with_field_subset(include_field_names=field_names)

    except ValueError:
        logger.warning("Invalid parameters for get_inventory_item", exc_info=True)
        raise
    except (
        InventoryAuthenticationError,
        InventoryNetworkError,
        InventoryAPIError,
        InventoryClientError,
    ):
        logger.exception("Inventory client error retrieving item")
        raise
    except Exception as exc:
        logger.exception("Unexpected error retrieving inventory item")
        raise InventoryClientError(f"Failed to retrieve inventory item {item_id}") from exc


async def list_inventory_items(
    limit: int = 50,
    skip: int = 0,
    surface: str | None = None,
    fetch_fields: InventoryFetchFieldsPresetName
    | list[str] = InventoryFetchFieldsPreset.MINIMAL.name,
) -> str:
    """List inventory items with pagination and optional surface filtering.

    Args:
        limit: Number of items to retrieve (1-1000, default: 50).
        skip: Number of items to skip for pagination (default: 0).
        surface: Optional surface filter (ENDPOINT, CLOUD, IDENTITY, NETWORK_DISCOVERY).
        fetch_fields: Field filtering (default: "MINIMAL"). Either:
                      - Preset name: "MINIMAL", "STANDARD", or "ALL"
                      - List of specific field names in camelCase (e.g., ["id", "resourceType"])
                      Field names must match those in InventoryFetchFieldsPreset.ALL.
                      **Note: type-hint is `list[str]` because `Iterable[str]` causes issues with FastMCP wrapping.**

    Returns:
        JSON string with paginated inventory items containing only requested fields.
        Fields without values are excluded (exclude_unset=True). Includes pagination metadata.

    Raises:
        ValueError: If limit/skip are invalid, if surface is invalid, if fetch_fields is empty,
                    if preset name is invalid, or if custom field names are not in ALL preset.
        InventoryAuthenticationError: If authentication fails.
        InventoryNetworkError: If network operation fails.
        InventoryAPIError: If the API returns an error.
        InventoryClientError: For other client-level errors.
    """
    try:
        # Validate parameters
        if limit < 1 or limit > MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
        if skip < 0:
            raise ValueError("skip must be non-negative")

        # Parse surface filter
        surface_enum: Surface | None = None
        if surface:
            try:
                surface_enum = Surface(surface)
            except ValueError:
                valid_surfaces = [s.value for s in Surface]
                raise ValueError(f"surface must be one of: {valid_surfaces}") from None

        # Parse and validate fetch_fields
        validated_aliases = _parse_fetch_fields(fetch_fields)
        # Map aliases to actual field names for Pydantic include parameter
        field_names = InventoryItem._map_aliases_to_field_names(validated_aliases)

        client = _get_inventory_client()
        async with client:
            response = await client.list_inventory(limit=limit, skip=skip, surface=surface_enum)

        return response.model_dump_json_with_field_subset(include_field_names=field_names)

    except ValueError:
        logger.warning("Invalid parameters for list_inventory_items", exc_info=True)
        raise
    except (
        InventoryAuthenticationError,
        InventoryNetworkError,
        InventoryAPIError,
        InventoryClientError,
    ):
        logger.exception("Inventory client error listing items")
        raise
    except Exception as exc:
        logger.exception("Unexpected error listing inventory items")
        raise InventoryClientError("Failed to list inventory items") from exc


async def search_inventory_items(
    filters: str | None = None,
    limit: int = 50,
    skip: int = 0,
    fetch_fields: InventoryFetchFieldsPresetName
    | list[str] = InventoryFetchFieldsPreset.MINIMAL.name,
) -> str:
    """Search inventory items using REST API filters.

    Note: This tool does not support surface filtering. For surface-specific
    queries (ENDPOINT, CLOUD, IDENTITY, NETWORK_DISCOVERY), use list_inventory_items instead.

    Args:
        filters: JSON string containing filter dictionary (optional).
        limit: Number of items to retrieve (1-1000, default: 50).
        skip: Number of items to skip for pagination (default: 0).
        fetch_fields: Field filtering (default: "MINIMAL"). Either:
                      - Preset name: "MINIMAL", "STANDARD", or "ALL"
                      - List of specific field names in camelCase (e.g., ["id", "resourceType"])
                      Field names must match those in InventoryFetchFieldsPreset.ALL.
                      **Note: type-hint is `list[str]` because `Iterable[str]` causes issues with FastMCP wrapping.**

    Returns:
        JSON string with filtered inventory items containing only requested fields.
        Fields without values are excluded (exclude_unset=True). Includes pagination metadata.
        Returns empty list if no matches found.

    Raises:
        ValueError: If filters JSON is invalid, if limit/skip are invalid, if fetch_fields is empty,
                    if preset name is invalid, or if custom field names are not in ALL preset.
        InventoryAuthenticationError: If authentication fails.
        InventoryNetworkError: If network operation fails.
        InventoryAPIError: If the API returns an error.
        InventoryClientError: For other client-level errors.
    """
    try:
        # Validate parameters
        if limit < 1 or limit > MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
        if skip < 0:
            raise ValueError("skip must be non-negative")

        # Parse filters
        filter_dict: JsonDict = {}
        if filters:
            try:
                parsed = json.loads(filters)
                if not isinstance(parsed, dict):
                    raise ValueError("Filters must be a dictionary/object")
                filter_dict = parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in filters parameter: {e}") from e

        # Parse and validate fetch_fields
        validated_aliases = _parse_fetch_fields(fetch_fields)
        # Map aliases to actual field names for Pydantic include parameter
        field_names = InventoryItem._map_aliases_to_field_names(validated_aliases)

        client = _get_inventory_client()
        async with client:
            response = await client.search_inventory(filters=filter_dict, limit=limit, skip=skip)

        return response.model_dump_json_with_field_subset(include_field_names=field_names)

    except ValueError:
        logger.warning("Invalid parameters for search_inventory_items", exc_info=True)
        raise
    except (
        InventoryAuthenticationError,
        InventoryNetworkError,
        InventoryAPIError,
        InventoryClientError,
    ):
        logger.exception("Inventory client error searching items")
        raise
    except Exception as exc:
        logger.exception("Unexpected error searching inventory items")
        raise InventoryClientError("Failed to search inventory items") from exc
