"""Integration tests for misconfigurations dynamic field selection.

These tests verify that custom field selection works correctly against the real API,
ensuring partial field sets are properly handled and nested objects can be expanded.

Tests require a valid .env file with:
- PURPLEMCP_CONSOLE_TOKEN: A valid API token
- PURPLEMCP_CONSOLE_BASE_URL: The console base URL

Tests will be skipped if environment is not configured or has no data.
"""

import pytest

from purple_mcp.config import get_settings
from purple_mcp.libs.misconfigurations import (
    MisconfigurationsClient,
    MisconfigurationsConfig,
    ViewType,
)


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
async def test_list_misconfigurations_minimal_fields(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with minimal field selection."""
    # Request only id field (minimal possible)
    result = await misconfigurations_client.list_misconfigurations(
        first=5, fields=["id"], view_type=ViewType.ALL
    )

    # Verify response structure
    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")

    # If there are misconfigurations, verify only id is present
    if result.edges:
        first_misconfiguration = result.edges[0].node
        assert first_misconfiguration.id is not None

        # Verify other fields are None (not requested)
        assert first_misconfiguration.name is None
        assert first_misconfiguration.severity is None
        assert first_misconfiguration.status is None
        assert first_misconfiguration.asset is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_summary_fields(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with summary field selection."""
    # Request typical summary fields
    result = await misconfigurations_client.list_misconfigurations(
        first=5,
        fields=["id", "name", "severity", "status", "detectedAt"],
        view_type=ViewType.ALL,
    )

    # Verify response structure
    assert result is not None
    assert hasattr(result, "edges")

    # If there are misconfigurations, verify requested fields are present
    if result.edges:
        first_misconfiguration = result.edges[0].node
        assert first_misconfiguration.id is not None
        assert first_misconfiguration.name is not None
        assert first_misconfiguration.severity is not None
        assert first_misconfiguration.status is not None
        assert first_misconfiguration.detected_at is not None

        # Verify non-requested fields are None
        assert first_misconfiguration.asset is None
        assert first_misconfiguration.scope is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_with_asset_fragment(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with asset nested object."""
    # Request fields including asset (should auto-expand)
    result = await misconfigurations_client.list_misconfigurations(
        first=5, fields=["id", "name", "severity", "asset"], view_type=ViewType.ALL
    )

    # Verify response structure
    assert result is not None

    # If there are misconfigurations, verify asset is populated
    if result.edges:
        first_misconfiguration = result.edges[0].node
        assert first_misconfiguration.id is not None
        assert first_misconfiguration.name is not None

        # Asset should be populated if present (may be None for some misconfigurations)
        if first_misconfiguration.asset:
            assert first_misconfiguration.asset.id is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_with_custom_asset_fragment(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with custom asset fragment."""
    # Request specific asset subfields
    result = await misconfigurations_client.list_misconfigurations(
        first=5,
        fields=["id", "name", "asset { id name type }"],
        view_type=ViewType.ALL,
    )

    # Verify response structure
    assert result is not None

    # If there are misconfigurations with assets, verify structure
    if result.edges:
        for edge in result.edges:
            misconfiguration = edge.node
            assert misconfiguration.id is not None

            if misconfiguration.asset:
                # These fields should be present
                assert misconfiguration.asset.id is not None
                # name and type might be None but should be in the model
                assert hasattr(misconfiguration.asset, "name")
                assert hasattr(misconfiguration.asset, "type")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_with_scope_fragment(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with scope nested object."""
    # Request fields including scope (should auto-expand)
    result = await misconfigurations_client.list_misconfigurations(
        first=5, fields=["id", "name", "scope"], view_type=ViewType.ALL
    )

    # Verify response structure
    assert result is not None

    # If there are misconfigurations, verify scope is populated
    if result.edges:
        first_misconfiguration = result.edges[0].node
        assert first_misconfiguration.id is not None

        # Scope should be populated if present
        if first_misconfiguration.scope:
            # At least one of account/site/group should be present
            assert (
                first_misconfiguration.scope.account is not None
                or first_misconfiguration.scope.site is not None
                or first_misconfiguration.scope.group is not None
            )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_with_custom_scope_fragment(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with custom scope fragment."""
    # Request specific scope subfields (deeply nested)
    result = await misconfigurations_client.list_misconfigurations(
        first=5,
        fields=["id", "scope { account { id name } }"],
        view_type=ViewType.ALL,
    )

    # Verify response structure
    assert result is not None

    # If there are misconfigurations with scope, verify structure
    if result.edges:
        for edge in result.edges:
            misconfiguration = edge.node
            assert misconfiguration.id is not None

            if misconfiguration.scope and misconfiguration.scope.account:
                # Account fields should be present
                assert misconfiguration.scope.account.id is not None
                assert hasattr(misconfiguration.scope.account, "name")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_with_cnapp_fragment(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with cnapp nested object."""
    # Request fields including cnapp (should auto-expand)
    result = await misconfigurations_client.list_misconfigurations(
        first=5, fields=["id", "name", "cnapp"], view_type=ViewType.ALL
    )

    # Verify response structure
    assert result is not None

    # If there are misconfigurations with cnapp data, verify structure
    if result.edges:
        for edge in result.edges:
            misconfiguration = edge.node
            assert misconfiguration.id is not None

            if misconfiguration.cnapp:
                # cnapp should have policy or verifiedExploitable
                assert hasattr(misconfiguration.cnapp, "policy")
                assert hasattr(misconfiguration.cnapp, "verified_exploitable")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_misconfigurations_with_custom_fields(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test searching misconfigurations with custom field selection."""
    # Search with filters and custom fields
    from purple_mcp.libs.misconfigurations.models import FilterInput

    filters = [
        FilterInput.model_validate(
            {
                "fieldId": "severity",
                "stringIn": {"values": ["HIGH", "CRITICAL"]},
            }
        )
    ]

    result = await misconfigurations_client.search_misconfigurations(
        filters=filters,
        first=10,
        fields=["id", "severity", "name", "status"],
        view_type=ViewType.ALL,
    )

    # Verify response structure
    assert result is not None

    # If there are results, verify requested fields are present
    if result.edges:
        for edge in result.edges:
            misconfiguration = edge.node
            assert misconfiguration.id is not None
            assert misconfiguration.severity in ["HIGH", "CRITICAL"]
            assert hasattr(misconfiguration, "name")
            assert hasattr(misconfiguration, "status")

            # Non-requested fields should be None
            assert misconfiguration.asset is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_pagination_with_minimal_fields(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test pagination efficiency with minimal field selection."""
    # Use minimal fields for efficient pagination
    page1 = await misconfigurations_client.list_misconfigurations(
        first=3, fields=["id"], view_type=ViewType.ALL
    )

    if not page1.edges or not page1.page_info.has_next_page:
        pytest.skip("Not enough misconfigurations for pagination test")
        return

    # Get second page
    page2 = await misconfigurations_client.list_misconfigurations(
        first=3, after=page1.page_info.end_cursor, fields=["id"], view_type=ViewType.ALL
    )

    # Verify pagination worked
    assert page2 is not None
    assert page2.edges

    # Verify no duplicate IDs across pages
    page1_ids = {edge.node.id for edge in page1.edges}
    page2_ids = {edge.node.id for edge in page2.edges}
    assert len(page1_ids & page2_ids) == 0, "Found duplicate IDs across pages"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_empty_fields_defaults_to_id(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test that empty fields list is coerced to ['id']."""
    # Pass empty list (should be coerced to ['id'])
    result = await misconfigurations_client.list_misconfigurations(
        first=5, fields=[], view_type=ViewType.ALL
    )

    # Verify response structure
    assert result is not None

    # If there are misconfigurations, verify only id is present
    if result.edges:
        first_misconfiguration = result.edges[0].node
        assert first_misconfiguration.id is not None

        # Other fields should be None
        assert first_misconfiguration.name is None
        assert first_misconfiguration.severity is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_misconfigurations_default_fields(
    misconfigurations_client: MisconfigurationsClient,
) -> None:
    """Test listing misconfigurations with default fields (fields=None)."""
    # Don't specify fields (should use defaults)
    result = await misconfigurations_client.list_misconfigurations(first=5, view_type=ViewType.ALL)

    # Verify response structure
    assert result is not None

    # If there are misconfigurations, verify default fields are populated
    if result.edges:
        first_misconfiguration = result.edges[0].node
        assert first_misconfiguration.id is not None
        assert first_misconfiguration.name is not None
        assert first_misconfiguration.severity is not None
        assert first_misconfiguration.status is not None
        assert first_misconfiguration.detected_at is not None

        # Default fields should include nested objects
        # (asset/scope may be None for some misconfigurations but should be queryable)
        assert hasattr(first_misconfiguration, "asset")
        assert hasattr(first_misconfiguration, "scope")
