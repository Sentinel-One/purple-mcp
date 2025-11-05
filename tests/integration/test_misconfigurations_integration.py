"""Integration tests for the Misconfigurations library.

These tests require a valid .env file with:
- PURPLEMCP_CONSOLE_TOKEN: A valid API token
- PURPLEMCP_CONSOLE_BASE_URL: The console base URL

Tests will be skipped if environment is not configured or has no data.
"""

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.misconfigurations import MisconfigurationsClient, MisconfigurationsConfig


@pytest.fixture
def misconfigurations_config(integration_env_check: dict[str, str]) -> MisconfigurationsConfig:
    """Create misconfigurations configuration from environment variables.

    Returns:
        MisconfigurationsConfig with settings from environment.
    """
    settings = get_settings()

    return MisconfigurationsConfig(
        graphql_url=settings.misconfigurations_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=30.0,
    )


@pytest.fixture
def misconfigurations_client(
    misconfigurations_config: MisconfigurationsConfig,
) -> MisconfigurationsClient:
    """Create a misconfigurations client instance."""
    return MisconfigurationsClient(misconfigurations_config)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with pagination."""
    # List first 5 misconfigurations
    result = await misconfigurations_client.list_misconfigurations(first=5)

    # Verify response structure
    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")

    # If there are misconfigurations, verify their structure
    if result.edges:
        first_misconfiguration = result.edges[0].node
        assert first_misconfiguration.id is not None
        assert first_misconfiguration.name is not None
        assert first_misconfiguration.severity is not None
        assert first_misconfiguration.status is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_misconfiguration(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test getting a specific misconfiguration by ID."""
    # First, list misconfigurations to get an ID
    list_result = await misconfigurations_client.list_misconfigurations(first=1)

    if not list_result.edges:
        pytest.skip("No misconfigurations available in the environment")
        return

    misconfiguration_id = list_result.edges[0].node.id

    # Now get the specific misconfiguration
    result = await misconfigurations_client.get_misconfiguration(misconfiguration_id)

    assert result is not None
    assert result.id == misconfiguration_id
    assert result.name is not None
    assert result.severity is not None
    assert result.status is not None
    assert result.asset is not None
    assert result.scope is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_misconfigurations_no_filters(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test searching misconfigurations without filters."""
    result = await misconfigurations_client.search_misconfigurations(filters=None, first=5)

    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_misconfiguration_notes(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test getting notes for a misconfiguration."""
    # First, list misconfigurations to get an ID
    list_result = await misconfigurations_client.list_misconfigurations(first=1)

    if not list_result.edges:
        pytest.skip("No misconfigurations available in the environment")
        return

    misconfiguration_id = list_result.edges[0].node.id

    # Get notes (may be empty)
    result = await misconfigurations_client.get_misconfiguration_notes(misconfiguration_id)

    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_misconfiguration_history(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test getting history for a misconfiguration."""
    # First, list misconfigurations to get an ID
    list_result = await misconfigurations_client.list_misconfigurations(first=1)

    if not list_result.edges:
        pytest.skip("No misconfigurations available in the environment")
        return

    misconfiguration_id = list_result.edges[0].node.id

    # Get history
    result = await misconfigurations_client.get_misconfiguration_history(
        misconfiguration_id, first=10
    )

    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")
