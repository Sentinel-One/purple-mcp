"""Unit tests for misconfigurations library dynamic field selection."""

from purple_mcp.libs.graphql_utils import build_node_fields
from purple_mcp.libs.misconfigurations.templates import DEFAULT_MISCONFIGURATION_FIELDS


class TestMisconfigurationsDefaultFields:
    """Test that default misconfiguration fields are properly defined."""

    def test_not_empty(self) -> None:
        """Test that DEFAULT_MISCONFIGURATION_FIELDS is not empty."""
        assert len(DEFAULT_MISCONFIGURATION_FIELDS) > 0

    def test_contains_required_fields(self) -> None:
        """Test that DEFAULT_MISCONFIGURATION_FIELDS contains essential fields."""
        required_fields = ["id", "severity", "status", "name"]
        field_string = " ".join(DEFAULT_MISCONFIGURATION_FIELDS)

        for field in required_fields:
            assert field in field_string


class TestMisconfigurationsBuildNodeFields:
    """Test build_node_fields with misconfiguration field defaults."""

    def test_with_none(self) -> None:
        """Test misconfigurations field builder with None."""
        result = build_node_fields(None, DEFAULT_MISCONFIGURATION_FIELDS)

        # Should contain all default fields
        for field in DEFAULT_MISCONFIGURATION_FIELDS:
            assert field in result

    def test_minimal(self) -> None:
        """Test misconfigurations field builder with minimal fields."""
        result = build_node_fields(["id"], DEFAULT_MISCONFIGURATION_FIELDS)

        assert "                id" in result
        assert "severity" not in result


class TestMisconfigurationsAutoExpansion:
    """Test auto-expansion of nested objects for misconfigurations."""

    def test_auto_expand_asset(self) -> None:
        """Test misconfiguration asset auto-expansion."""
        result = build_node_fields(["id", "asset"], DEFAULT_MISCONFIGURATION_FIELDS)

        assert "                id" in result
        # Should contain the full nested asset structure
        assert "asset {" in result
        assert "id" in result
        assert "name" in result

    def test_auto_expand_assignee(self) -> None:
        """Test misconfiguration assignee auto-expansion."""
        result = build_node_fields(["id", "assignee"], DEFAULT_MISCONFIGURATION_FIELDS)

        assert "                id" in result
        assert "assignee { id email fullName }" in result


class TestMisconfigurationsPartialAssetFragments:
    """Test partial asset fragments for misconfigurations with optional Asset fields."""

    def test_partial_asset_fragment(self) -> None:
        """Test misconfiguration with partial asset fields (id, name, type only)."""
        fields = ["id", "severity", "asset { id name type }"]
        result = build_node_fields(fields, DEFAULT_MISCONFIGURATION_FIELDS)

        assert "                id" in result
        assert "                severity" in result
        assert "                asset { id name type }" in result
        # Should not expand to full asset fragment
        assert "category" not in result or "asset { id name type }" in result

    def test_minimal_asset_fragment(self) -> None:
        """Test misconfiguration with minimal asset (id only)."""
        fields = ["id", "severity", "asset { id }"]
        result = build_node_fields(fields, DEFAULT_MISCONFIGURATION_FIELDS)

        assert "                id" in result
        assert "                severity" in result
        assert "                asset { id }" in result
        # Should not have expanded fields
        assert "asset { id name type }" not in result

    def test_custom_asset_fields(self) -> None:
        """Test misconfiguration with custom asset field selection."""
        fields = ["id", "asset { id name domain privileged }"]
        result = build_node_fields(fields, DEFAULT_MISCONFIGURATION_FIELDS)

        assert "                id" in result
        assert "                asset { id name domain privileged }" in result
