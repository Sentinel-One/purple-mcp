"""Integration tests for all misconfigurations fields to ensure API compatibility.

These tests verify that every field in the misconfigurations API can be queried successfully
and returns data in the expected format. This helps catch upstream API changes early.
"""

import pytest

from purple_mcp.libs.misconfigurations.client import MisconfigurationsClient
from purple_mcp.libs.misconfigurations.config import MisconfigurationsConfig
from purple_mcp.libs.misconfigurations.templates import DEFAULT_MISCONFIGURATION_FIELDS

pytestmark = pytest.mark.integration


@pytest.fixture
def misconfig_config() -> MisconfigurationsConfig:
    """Create MisconfigurationsConfig for integration tests."""
    from purple_mcp.config import get_settings

    settings = get_settings()
    return MisconfigurationsConfig(
        graphql_url=settings.misconfigurations_graphql_url,
        auth_token=settings.graphql_service_token,
        timeout=60.0,
    )


@pytest.fixture
def misconfig_client(
    misconfig_config: MisconfigurationsConfig,
) -> MisconfigurationsClient:
    """Create MisconfigurationsClient for integration tests."""
    return MisconfigurationsClient(misconfig_config)


class TestAllMisconfigurationsFields:
    """Test that every misconfigurations field can be queried successfully."""

    @pytest.mark.asyncio
    async def test_all_default_fields(self, misconfig_client: MisconfigurationsClient) -> None:
        """Test querying with all default fields at once."""
        # Query with all fields to ensure they all work together
        result = await misconfig_client.list_misconfigurations(
            first=1,  # Just get one misconfiguration
            fields=DEFAULT_MISCONFIGURATION_FIELDS,
        )

        # Should return successfully without errors
        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_individual_simple_fields(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test each simple field individually."""
        simple_fields = [
            "id",
            "externalId",
            "name",
            "severity",
            "status",
            "detectedAt",
            "lastSeenAt",
            "eventTime",
            "product",
            "vendor",
            "environment",
            "analystVerdict",
            "misconfigurationType",
            "mitigable",
            "exposureReason",
            "organization",
            "enforcementAction",
            "resourceUid",
            "exclusionPolicyId",
            "exploitId",
            "complianceStandards",
            "dataClassificationCategories",
            "dataClassificationDataTypes",
        ]

        for field in simple_fields:
            # Test each field individually
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field] if field != "id" else ["id"],
            )

            assert result.edges is not None, f"Field '{field}' failed"
            assert isinstance(result.edges, list), f"Field '{field}' returned non-list"

    @pytest.mark.asyncio
    async def test_nested_asset_fields(self, misconfig_client: MisconfigurationsClient) -> None:
        """Test all asset nested fields."""
        # Test default asset fragment
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=["id", "asset { id name type }"],
        )
        assert result.edges is not None

        # Test asset with cloudInfo (cloudInfo should NOT get id prepended)
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=["id", "asset { id cloudInfo { accountId region } }"],
        )
        assert result.edges is not None

        # Test asset with kubernetesInfo (kubernetesInfo should NOT get id prepended)
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=["id", "asset { id kubernetesInfo { cluster namespace } }"],
        )
        assert result.edges is not None

    @pytest.mark.asyncio
    async def test_nested_scope_fields(self, misconfig_client: MisconfigurationsClient) -> None:
        """Test all scope nested fields."""
        # Test default scope fragment
        result = await misconfig_client.list_misconfigurations(
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
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Scope field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_cnapp_fields(self, misconfig_client: MisconfigurationsClient) -> None:
        """Test all cnapp nested fields."""
        # Test default cnapp fragment
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=["id", "cnapp { policy { id version group } verifiedExploitable }"],
        )
        assert result.edges is not None

        # Test partial cnapp fields
        partial_fields = [
            "cnapp { policy { id } }",
            "cnapp { policy { id version } }",
            "cnapp { verifiedExploitable }",
        ]

        for field in partial_fields:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Cnapp field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_evidence_fields(self, misconfig_client: MisconfigurationsClient) -> None:
        """Test all evidence nested fields."""
        # Test default evidence fragment
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=["id", "evidence { fileName fileType iacFramework }"],
        )
        assert result.edges is not None

        # Test partial evidence fields
        partial_fields = [
            "evidence { fileName }",
            "evidence { ipAddress port }",
            "evidence { subdomain }",
        ]

        for field in partial_fields:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Evidence field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_admission_request_fields(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test all admissionRequest nested fields."""
        # Test default admissionRequest fragment
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=[
                "id",
                "admissionRequest { category resourceName resourceNamespace }",
            ],
        )
        assert result.edges is not None

        # Test partial admissionRequest fields
        partial_fields = [
            "admissionRequest { resourceName }",
            "admissionRequest { resourceType userName }",
            "admissionRequest { userUid userGroup }",
        ]

        for field in partial_fields:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"AdmissionRequest field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_remediation_fields(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test all remediation nested fields."""
        # Test default remediation fragment
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=["id", "remediation { mitigable mitigationSteps }"],
        )
        assert result.edges is not None

        # Test partial remediation fields
        partial_fields = [
            "remediation { mitigable }",
            "remediation { mitigationSteps }",
        ]

        for field in partial_fields:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Remediation field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_mitre_attacks_fields(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test all mitreAttacks nested fields."""
        # Test default mitreAttacks fragment
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=[
                "id",
                "mitreAttacks { techniqueId techniqueName techniqueUrl tacticName }",
            ],
        )
        assert result.edges is not None

        # Test partial mitreAttacks fields
        partial_fields = [
            "mitreAttacks { techniqueId }",
            "mitreAttacks { techniqueName tacticName }",
            "mitreAttacks { techniqueUrl }",
        ]

        for field in partial_fields:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"MitreAttacks field '{field}' failed"

    @pytest.mark.asyncio
    async def test_nested_assignee_fields(self, misconfig_client: MisconfigurationsClient) -> None:
        """Test all assignee nested fields including partial selections without id."""
        # Test default assignee fragment
        result = await misconfig_client.list_misconfigurations(
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
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Assignee field '{field}' failed"

    @pytest.mark.asyncio
    async def test_minimal_field_selection(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test that minimal field selection (just id) works."""
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=["id"],
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_deep_asset_nesting_combinations(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test deep nesting with asset cloudInfo and kubernetesInfo combinations."""
        combinations = [
            # CloudInfo with all fields
            "asset { id name cloudInfo { accountId accountName providerName region } }",
            # KubernetesInfo with all fields
            "asset { id name kubernetesInfo { cluster namespace } }",
            # Both together
            "asset { id cloudInfo { region } kubernetesInfo { cluster } }",
            # Asset with all top-level fields
            "asset { id externalId name type category subcategory privileged }",
        ]

        for field in combinations:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Asset combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_cnapp_policy_combinations(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test cnapp with different policy field combinations."""
        combinations = [
            "cnapp { policy { id } }",
            "cnapp { policy { id version } }",
            "cnapp { policy { id version group } }",
            "cnapp { verifiedExploitable }",
            "cnapp { policy { id } verifiedExploitable }",
        ]

        for field in combinations:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Cnapp combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_evidence_field_combinations(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test evidence with different field combinations."""
        combinations = [
            "evidence { fileName }",
            "evidence { fileName fileType }",
            "evidence { iacFramework }",
            "evidence { ipAddress port }",
            "evidence { subdomain }",
            "evidence { fileName fileType iacFramework ipAddress port subdomain }",
        ]

        for field in combinations:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Evidence combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_scope_partial_selections(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test scope with different combinations of account/site/group."""
        combinations = [
            "scope { account { id } }",
            "scope { site { id } }",
            "scope { group { id } }",
            "scope { account { name } }",
            "scope { account { id name } site { name } }",
            "scope { account { id } site { id } group { id } }",
        ]

        for field in combinations:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"Scope combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_admission_request_combinations(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test admissionRequest with different field combinations."""
        combinations = [
            "admissionRequest { category }",
            "admissionRequest { resourceName resourceNamespace }",
            "admissionRequest { resourceType userName }",
            "admissionRequest { userUid userGroup }",
            "admissionRequest { category resourceName resourceNamespace resourceType userName userUid userGroup }",
        ]

        for field in combinations:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"AdmissionRequest combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_mitre_attacks_combinations(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test mitreAttacks with different field combinations."""
        combinations = [
            "mitreAttacks { techniqueId }",
            "mitreAttacks { techniqueName tacticName }",
            "mitreAttacks { techniqueUrl }",
            "mitreAttacks { tacticUid }",
            "mitreAttacks { techniqueId techniqueName techniqueUrl tacticName tacticUid }",
        ]

        for field in combinations:
            result = await misconfig_client.list_misconfigurations(
                first=1,
                fields=["id", field],
            )
            assert result.edges is not None, f"MitreAttacks combination '{field}' failed"

    @pytest.mark.asyncio
    async def test_multiple_nested_objects_together(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test querying multiple nested objects simultaneously."""
        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=[
                "id",
                "severity",
                "status",
                "asset { id name type }",
                "scope { account { id } site { id } }",
                "cnapp { policy { id } verifiedExploitable }",
                "evidence { fileName iacFramework }",
                "admissionRequest { category resourceName }",
                "mitreAttacks { techniqueId tacticName }",
                "remediation { mitigable }",
                "assignee { id email }",
            ],
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_maximal_field_selection(
        self, misconfig_client: MisconfigurationsClient
    ) -> None:
        """Test requesting all default fields at once."""
        from purple_mcp.libs.misconfigurations.templates import DEFAULT_MISCONFIGURATION_FIELDS

        result = await misconfig_client.list_misconfigurations(
            first=1,
            fields=DEFAULT_MISCONFIGURATION_FIELDS,
        )

        assert result.edges is not None
        assert isinstance(result.edges, list)
