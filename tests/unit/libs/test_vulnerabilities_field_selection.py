"""Unit tests for vulnerabilities library dynamic field selection."""

from purple_mcp.libs.graphql_utils import build_node_fields
from purple_mcp.libs.vulnerabilities.templates import DEFAULT_VULNERABILITY_FIELDS


class TestVulnerabilitiesDefaultFields:
    """Test that default vulnerability fields are properly defined."""

    def test_not_empty(self) -> None:
        """Test that DEFAULT_VULNERABILITY_FIELDS is not empty."""
        assert len(DEFAULT_VULNERABILITY_FIELDS) > 0

    def test_contains_required_fields(self) -> None:
        """Test that DEFAULT_VULNERABILITY_FIELDS contains essential fields."""
        required_fields = ["id", "severity", "status", "name"]
        field_string = " ".join(DEFAULT_VULNERABILITY_FIELDS)

        for field in required_fields:
            assert field in field_string


class TestVulnerabilitiesBuildNodeFields:
    """Test build_node_fields with vulnerability field defaults."""

    def test_with_none(self) -> None:
        """Test vulnerabilities field builder with None."""
        result = build_node_fields(None, DEFAULT_VULNERABILITY_FIELDS)

        # Should contain all default fields
        for field in DEFAULT_VULNERABILITY_FIELDS:
            assert field in result

    def test_minimal(self) -> None:
        """Test vulnerabilities field builder with minimal fields."""
        result = build_node_fields(["id"], DEFAULT_VULNERABILITY_FIELDS)

        assert "                id" in result
        assert "severity" not in result


class TestVulnerabilitiesAutoExpansion:
    """Test auto-expansion of nested objects for vulnerabilities."""

    def test_auto_expand_asset(self) -> None:
        """Test vulnerability asset auto-expansion."""
        result = build_node_fields(["id", "asset"], DEFAULT_VULNERABILITY_FIELDS)

        assert "                id" in result
        assert "asset {" in result

    def test_auto_expand_cve(self) -> None:
        """Test vulnerability CVE auto-expansion."""
        result = build_node_fields(["id", "cve"], DEFAULT_VULNERABILITY_FIELDS)

        assert "                id" in result
        assert "cve {" in result
        assert "id" in result
        assert "nvdBaseScore" in result

    def test_auto_expand_software(self) -> None:
        """Test vulnerability software auto-expansion."""
        # software does NOT have an id field in the schema, so id will NOT be auto-prepended
        result = build_node_fields(["id", "software"], DEFAULT_VULNERABILITY_FIELDS)

        assert "                id" in result
        assert "software { name version fixVersion type vendor }" in result


class TestVulnerabilitiesPartialAssetFragments:
    """Test partial asset fragments for vulnerabilities with optional Asset fields."""

    def test_partial_asset_fragment(self) -> None:
        """Test vulnerability with partial asset fields (id, name, type only)."""
        fields = ["id", "severity", "asset { id name type }"]
        result = build_node_fields(fields, DEFAULT_VULNERABILITY_FIELDS)

        assert "                id" in result
        assert "                severity" in result
        assert "                asset { id name type }" in result

    def test_minimal_asset_fragment(self) -> None:
        """Test vulnerability with minimal asset (id only)."""
        fields = ["id", "severity", "asset { id }"]
        result = build_node_fields(fields, DEFAULT_VULNERABILITY_FIELDS)

        assert "                id" in result
        assert "                severity" in result
        assert "                asset { id }" in result
        # Should not have expanded fields
        assert "asset { id name type }" not in result

    def test_custom_asset_fields(self) -> None:
        """Test vulnerability with custom asset field selection."""
        fields = ["id", "asset { id name domain privileged }"]
        result = build_node_fields(fields, DEFAULT_VULNERABILITY_FIELDS)

        assert "                id" in result
        assert "                asset { id name domain privileged }" in result
