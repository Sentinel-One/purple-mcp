"""Integration tests for the Vulnerabilities library.

These tests require a valid .env file with:
- PURPLEMCP_CONSOLE_TOKEN: A valid API token
- PURPLEMCP_CONSOLE_BASE_URL: The console base URL

Tests will be skipped if environment is not configured or has no data.
"""

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.vulnerabilities import VulnerabilitiesClient, VulnerabilitiesConfig


@pytest.fixture
def vulnerabilities_config(integration_env_check: dict[str, str]) -> VulnerabilitiesConfig:
    """Create vulnerabilities configuration from environment variables.

    Returns:
        VulnerabilitiesConfig with settings from environment.
    """
    settings = get_settings()

    return VulnerabilitiesConfig(
        graphql_url=settings.vulnerabilities_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=30.0,
    )


@pytest.fixture
def vulnerabilities_client(
    vulnerabilities_config: VulnerabilitiesConfig,
) -> VulnerabilitiesClient:
    """Create a vulnerabilities client instance."""
    return VulnerabilitiesClient(vulnerabilities_config)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with pagination."""
    # List first 5 vulnerabilities
    result = await vulnerabilities_client.list_vulnerabilities(first=5)

    # Verify response structure
    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")

    # If there are vulnerabilities, verify their structure
    if result.edges:
        first_vulnerability = result.edges[0].node
        assert first_vulnerability.id is not None
        assert first_vulnerability.name is not None
        assert first_vulnerability.severity is not None
        assert first_vulnerability.status is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_vulnerability(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test getting a specific vulnerability by ID."""
    # First, list vulnerabilities to get an ID
    list_result = await vulnerabilities_client.list_vulnerabilities(first=1)

    if not list_result.edges:
        pytest.skip("No vulnerabilities available in the environment")
        return

    vulnerability_id = list_result.edges[0].node.id

    # Now get the specific vulnerability
    result = await vulnerabilities_client.get_vulnerability(vulnerability_id)

    assert result is not None
    assert result.id == vulnerability_id
    assert result.name is not None
    assert result.severity is not None
    assert result.status is not None
    assert result.asset is not None
    assert result.scope is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_vulnerabilities_no_filters(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test searching vulnerabilities without filters."""
    result = await vulnerabilities_client.search_vulnerabilities(filters=None, first=5)

    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_vulnerability_notes(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test getting notes for a vulnerability."""
    # First, list vulnerabilities to get an ID
    list_result = await vulnerabilities_client.list_vulnerabilities(first=1)

    if not list_result.edges:
        pytest.skip("No vulnerabilities available in the environment")
        return

    vulnerability_id = list_result.edges[0].node.id

    # Get notes (may be empty)
    result = await vulnerabilities_client.get_vulnerability_notes(vulnerability_id)

    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_vulnerability_history(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test getting history for a vulnerability."""
    # First, list vulnerabilities to get an ID
    list_result = await vulnerabilities_client.list_vulnerabilities(first=1)

    if not list_result.edges:
        pytest.skip("No vulnerabilities available in the environment")
        return

    vulnerability_id = list_result.edges[0].node.id

    # Get history
    result = await vulnerabilities_client.get_vulnerability_history(vulnerability_id, first=10)

    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_pagination(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test pagination with vulnerabilities."""
    # Get first page
    first_page = await vulnerabilities_client.list_vulnerabilities(first=2)

    if not first_page.edges or len(first_page.edges) < 2:
        pytest.skip("Not enough vulnerabilities for pagination test")
        return

    # If there's a next page, get it
    if first_page.page_info.has_next_page and first_page.page_info.end_cursor:
        second_page = await vulnerabilities_client.list_vulnerabilities(
            first=2, after=first_page.page_info.end_cursor
        )

        assert second_page is not None
        assert hasattr(second_page, "edges")
        # Verify we got different data
        if second_page.edges:
            assert second_page.edges[0].node.id != first_page.edges[0].node.id
