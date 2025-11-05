"""Integration tests for all vulnerabilities fields to ensure API compatibility.

These tests verify that every field in the vulnerabilities API can be queried successfully
and returns data in the expected format. This helps catch upstream API changes early.
"""

import pytest

from purple_mcp.libs.vulnerabilities.client import VulnerabilitiesClient
from purple_mcp.libs.vulnerabilities.config import VulnerabilitiesConfig
from purple_mcp.libs.vulnerabilities.templates import DEFAULT_VULNERABILITY_FIELDS

pytestmark = pytest.mark.integration


@pytest.fixture
def vuln_config() -> VulnerabilitiesConfig:
    """Create VulnerabilitiesConfig for integration tests."""
    from purple_mcp.config import get_settings

    settings = get_settings()
    return VulnerabilitiesConfig(
        graphql_url=settings.vulnerabilities_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,
    )


@pytest.fixture
def vuln_client(vuln_config: VulnerabilitiesConfig) -> VulnerabilitiesClient:
    """Create VulnerabilitiesClient for integration tests."""
    return VulnerabilitiesClient(vuln_config)


class TestAllVulnerabilitiesFields:
    """Test that every vulnerabilities field can be queried successfully."""

    @pytest.mark.asyncio
    async def test_all_default_fields(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test querying with all default fields at once."""
        # Query with all fields to ensure they all work together
        result = await vuln_client.list_vulnerabilities(
            first=1,  # Just get one vulnerability
            fields=DEFAULT_VULNERABILITY_FIELDS,
        )

        # Should return successfully without errors
        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_individual_simple_fields(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test each simple field individually."""
        simple_fields = [
            "id",
            "name",
            "severity",
            "status",
            "detectedAt",
            "lastSeenAt",
            "product",
            "vendor",
            "analystVerdict",
            "exclusionPolicyId",
        ]

        for field in simple_fields:
            # Test each field individually
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field] if field != "id" else ["id"],
            )

            assert result.edges is not None, f"Field '{field}' failed"
            assert isinstance(result.edges, list), f"Field '{field}' returned non-list"

    @pytest.mark.asyncio
    async def test_nested_asset_fields(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test all asset nested fields."""
        # Test default asset fragment
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id", "asset { id name type }"],
        )
        assert result.edges is not None

        # Test asset with cloudInfo (cloudInfo should NOT get id prepended)
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id", "asset { id cloudInfo { accountId region } }"],
        )
        assert result.edges is not None

        # Test asset with kubernetesInfo (kubernetesInfo should NOT get id prepended)
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id", "asset { id kubernetesInfo { cluster namespace } }"],
        )
        assert result.edges is not None

    @pytest.mark.asyncio
    async def test_nested_cve_fields(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test all cve nested fields."""
        # Test default cve fragment
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id", "cve { id nvdBaseScore riskScore publishedDate }"],
        )
        assert result.edges is not None

        # Test partial cve fields
        partial_fields = [
            "cve { id }",
            "cve { id nvdBaseScore }",
            "cve { id exploitMaturity }",
            "cve { id exploitedInTheWild }",
            "cve { id epssScore }",
        ]

        for field in partial_fields:
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"CVE field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_software_fields(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test all software nested fields."""
        # Test default software fragment
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id", "software { name version fixVersion type vendor }"],
        )
        assert result.edges is not None

        # Test partial software fields
        partial_fields = [
            "software { name }",
            "software { name version }",
            "software { name fixVersion }",
            "software { name type vendor }",
        ]

        for field in partial_fields:
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Software field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_scope_fields(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test all scope nested fields."""
        # Test default scope fragment
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id", "scope { account { id name } site { id name } }"],
        )
        assert result.edges is not None

        # Test partial scope fields (account might be None with partial selection)
        partial_fields = [
            "scope { site { id } }",
            "scope { group { id } }",
            "scope { account { id } site { id } }",
        ]

        for field in partial_fields:
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Scope field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_assignee_fields(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test all assignee nested fields including partial selections without id."""
        # Test default assignee fragment
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id", "assignee { id email fullName }"],
        )
        assert result.edges is not None

        # Test partial assignee fields (including without id to test optional id field)
        partial_fields = [
            "assignee { id }",
            "assignee { email }",  # Tests User.id being optional
            "assignee { fullName }",  # Tests User.id being optional
            "assignee { id email }",
            "assignee { email fullName }",  # Tests User.id being optional
        ]

        for field in partial_fields:
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Assignee field '{field}' failed"

    @pytest.mark.asyncio
    async def test_minimal_field_selection(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test that minimal field selection (just id) works."""
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=["id"],
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_deep_asset_nesting_combinations(
        self, vuln_client: VulnerabilitiesClient
    ) -> None:
        """Test deep nesting with asset cloudInfo and kubernetesInfo combinations."""
        combinations = [
            # CloudInfo only
            "asset { id name cloudInfo { accountId region } }",
            # KubernetesInfo only
            "asset { id name kubernetesInfo { cluster namespace } }",
            # Both together
            "asset { id name cloudInfo { accountId accountName region } kubernetesInfo { cluster } }",
            # All asset subfields
            "asset { id name type category subcategory privileged cloudInfo { accountId } }",
        ]

        for field in combinations:
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Asset combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_cve_field_combinations(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test different CVE field combinations."""
        combinations = [
            "cve { id nvdBaseScore }",
            "cve { id riskScore exploitMaturity }",
            "cve { id epssScore exploitedInTheWild }",
            "cve { id nvdBaseScore riskScore publishedDate epssScore exploitMaturity exploitedInTheWild }",
        ]

        for field in combinations:
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"CVE combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_multiple_nested_objects_together(
        self, vuln_client: VulnerabilitiesClient
    ) -> None:
        """Test querying multiple nested objects simultaneously."""
        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=[
                "id",
                "severity",
                "asset { id name type }",
                "cve { id nvdBaseScore riskScore }",
                "software { name version fixVersion }",
                "scope { account { id } site { id } }",
                "assignee { id email }",
            ],
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_scope_partial_selections(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test scope with different combinations of account/site/group."""
        combinations = [
            "scope { account { id } }",
            "scope { site { id } }",
            "scope { group { id } }",
            "scope { account { id name } site { name } }",
            "scope { account { id } site { id } group { id } }",
        ]

        for field in combinations:
            result = await vuln_client.list_vulnerabilities(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Scope combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_maximal_field_selection(self, vuln_client: VulnerabilitiesClient) -> None:
        """Test requesting all default fields at once."""
        from purple_mcp.libs.vulnerabilities.templates import DEFAULT_VULNERABILITY_FIELDS

        result = await vuln_client.list_vulnerabilities(
            first=1,
            fields=DEFAULT_VULNERABILITY_FIELDS,
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)
