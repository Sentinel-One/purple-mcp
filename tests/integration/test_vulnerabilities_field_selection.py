"""Integration tests for vulnerabilities dynamic field selection.

These tests verify that custom field selection works correctly against the real API,
ensuring partial field sets are properly handled and nested objects can be expanded.

Tests require a valid .env file with:
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
async def test_list_vulnerabilities_minimal_fields(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with minimal field selection."""
    # Request only id field (minimal possible)
    result = await vulnerabilities_client.list_vulnerabilities(first=5, fields=["id"])

    # Verify response structure
    assert result is not None
    assert hasattr(result, "edges")
    assert hasattr(result, "page_info")

    # If there are vulnerabilities, verify only id is present
    if result.edges:
        first_vulnerability = result.edges[0].node
        assert first_vulnerability.id is not None

        # Verify other fields are None (not requested)
        assert first_vulnerability.name is None
        assert first_vulnerability.severity is None
        assert first_vulnerability.status is None
        assert first_vulnerability.asset is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_summary_fields(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with summary field selection."""
    # Request typical summary fields
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5,
        fields=["id", "name", "severity", "status", "detectedAt"],
    )

    # Verify response structure
    assert result is not None
    assert hasattr(result, "edges")

    # If there are vulnerabilities, verify requested fields are present
    if result.edges:
        first_vulnerability = result.edges[0].node
        assert first_vulnerability.id is not None
        assert first_vulnerability.name is not None
        assert first_vulnerability.severity is not None
        assert first_vulnerability.status is not None
        assert first_vulnerability.detected_at is not None

        # Verify non-requested fields are None
        assert first_vulnerability.asset is None
        assert first_vulnerability.cve is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_asset_fragment(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with asset nested object."""
    # Request fields including asset (should auto-expand)
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5, fields=["id", "name", "severity", "asset"]
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities, verify asset is populated
    if result.edges:
        first_vulnerability = result.edges[0].node
        assert first_vulnerability.id is not None
        assert first_vulnerability.name is not None

        # Asset should be populated if present (may be None for some vulnerabilities)
        if first_vulnerability.asset:
            assert first_vulnerability.asset.id is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_custom_asset_fragment(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with custom asset fragment."""
    # Request specific asset subfields
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5,
        fields=["id", "name", "asset { id name type }"],
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities with assets, verify structure
    if result.edges:
        for edge in result.edges:
            vulnerability = edge.node
            assert vulnerability.id is not None

            if vulnerability.asset:
                # These fields should be present
                assert vulnerability.asset.id is not None
                # name and type might be None but should be in the model
                assert hasattr(vulnerability.asset, "name")
                assert hasattr(vulnerability.asset, "type")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_scope_fragment(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with scope nested object."""
    # Request fields including scope (should auto-expand)
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5, fields=["id", "name", "scope"]
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities, verify scope is populated
    if result.edges:
        first_vulnerability = result.edges[0].node
        assert first_vulnerability.id is not None

        # Scope should be populated if present
        if first_vulnerability.scope:
            # At least one of account/site/group should be present
            assert (
                first_vulnerability.scope.account is not None
                or first_vulnerability.scope.site is not None
                or first_vulnerability.scope.group is not None
            )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_custom_scope_fragment(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with custom scope fragment."""
    # Request specific scope subfields (deeply nested)
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5,
        fields=["id", "scope { account { id name } }"],
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities with scope, verify structure
    if result.edges:
        for edge in result.edges:
            vulnerability = edge.node
            assert vulnerability.id is not None

            if vulnerability.scope and vulnerability.scope.account:
                # Account fields should be present
                assert vulnerability.scope.account.id is not None
                assert hasattr(vulnerability.scope.account, "name")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_cve_fragment(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with cve nested object."""
    # Request fields including cve (should auto-expand)
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5, fields=["id", "name", "cve"]
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities with CVE data, verify structure
    if result.edges:
        for edge in result.edges:
            vulnerability = edge.node
            assert vulnerability.id is not None

            if vulnerability.cve:
                # CVE should have an id
                assert vulnerability.cve.id is not None
                # Other fields like nvdBaseScore might be None but should be in the model
                assert hasattr(vulnerability.cve, "nvd_base_score")
                assert hasattr(vulnerability.cve, "risk_score")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_custom_cve_fragment(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with custom cve fragment."""
    # Request specific cve subfields
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5,
        fields=["id", "name", "cve { id nvdBaseScore riskScore }"],
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities with CVE data, verify structure
    if result.edges:
        for edge in result.edges:
            vulnerability = edge.node
            assert vulnerability.id is not None

            if vulnerability.cve:
                # Requested fields should be present
                assert vulnerability.cve.id is not None
                assert hasattr(vulnerability.cve, "nvd_base_score")
                assert hasattr(vulnerability.cve, "risk_score")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_software_fragment(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with software nested object."""
    # Request fields including software (should auto-expand)
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5, fields=["id", "name", "software"]
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities with software data, verify structure
    if result.edges:
        for edge in result.edges:
            vulnerability = edge.node
            assert vulnerability.id is not None

            if vulnerability.software:
                # Software should have fields
                assert hasattr(vulnerability.software, "name")
                assert hasattr(vulnerability.software, "version")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_vulnerabilities_with_custom_fields(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test searching vulnerabilities with custom field selection."""
    # Search with filters and custom fields
    from purple_mcp.libs.vulnerabilities.models import FilterInput

    filters = [
        FilterInput.model_validate(
            {
                "fieldId": "severity",
                "stringIn": {"values": ["HIGH", "CRITICAL"]},
            }
        )
    ]

    result = await vulnerabilities_client.search_vulnerabilities(
        filters=filters,
        first=10,
        fields=["id", "severity", "name", "status"],
    )

    # Verify response structure
    assert result is not None

    # If there are results, verify requested fields are present
    if result.edges:
        for edge in result.edges:
            vulnerability = edge.node
            assert vulnerability.id is not None
            assert vulnerability.severity in ["HIGH", "CRITICAL"]
            assert hasattr(vulnerability, "name")
            assert hasattr(vulnerability, "status")

            # Non-requested fields should be None
            assert vulnerability.asset is None
            assert vulnerability.cve is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_pagination_with_minimal_fields(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test pagination efficiency with minimal field selection."""
    # Use minimal fields for efficient pagination
    page1 = await vulnerabilities_client.list_vulnerabilities(first=3, fields=["id"])

    if not page1.edges or not page1.page_info.has_next_page:
        pytest.skip("Not enough vulnerabilities for pagination test")
        return

    # Get second page
    page2 = await vulnerabilities_client.list_vulnerabilities(
        first=3, after=page1.page_info.end_cursor, fields=["id"]
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
async def test_list_vulnerabilities_empty_fields_defaults_to_id(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test that empty fields list is coerced to ['id']."""
    # Pass empty list (should be coerced to ['id'])
    result = await vulnerabilities_client.list_vulnerabilities(first=5, fields=[])

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities, verify only id is present
    if result.edges:
        first_vulnerability = result.edges[0].node
        assert first_vulnerability.id is not None

        # Other fields should be None
        assert first_vulnerability.name is None
        assert first_vulnerability.severity is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_default_fields(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with default fields (fields=None)."""
    # Don't specify fields (should use defaults)
    result = await vulnerabilities_client.list_vulnerabilities(first=5)

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities, verify default fields are populated
    if result.edges:
        first_vulnerability = result.edges[0].node
        assert first_vulnerability.id is not None
        assert first_vulnerability.name is not None
        assert first_vulnerability.severity is not None
        assert first_vulnerability.status is not None
        assert first_vulnerability.detected_at is not None

        # Default fields should include nested objects
        # (asset/cve/software may be None for some vulnerabilities but should be queryable)
        assert hasattr(first_vulnerability, "asset")
        assert hasattr(first_vulnerability, "cve")
        assert hasattr(first_vulnerability, "software")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_vulnerabilities_with_deeply_nested_asset(
    vulnerabilities_client: VulnerabilitiesClient,
) -> None:
    """Test listing vulnerabilities with deeply nested asset fragment."""
    # Request asset with cloudInfo subfields
    result = await vulnerabilities_client.list_vulnerabilities(
        first=5,
        fields=["id", "asset { id cloudInfo { accountId region } }"],
    )

    # Verify response structure
    assert result is not None

    # If there are vulnerabilities with cloud assets, verify structure
    if result.edges:
        for edge in result.edges:
            vulnerability = edge.node
            assert vulnerability.id is not None

            if vulnerability.asset and vulnerability.asset.cloud_info:
                # CloudInfo fields should be present
                assert hasattr(vulnerability.asset.cloud_info, "account_id")
                assert hasattr(vulnerability.asset.cloud_info, "region")
