"""Unit tests for alerts library dynamic field selection."""

from purple_mcp.libs.alerts.client import ALLOWED_ALERT_FIELDS, DEFAULT_ALERT_FIELDS
from purple_mcp.libs.graphql_utils import build_node_fields


class TestAlertsDefaultFields:
    """Test that default alert fields are properly defined."""

    def test_not_empty(self) -> None:
        """Test that DEFAULT_ALERT_FIELDS is not empty."""
        assert len(DEFAULT_ALERT_FIELDS) > 0

    def test_contains_required_fields(self) -> None:
        """Test that DEFAULT_ALERT_FIELDS contains essential fields."""
        required_fields = ["id", "severity", "status", "name"]
        field_string = " ".join(DEFAULT_ALERT_FIELDS)

        for field in required_fields:
            assert field in field_string


class TestAlertsBuildNodeFields:
    """Test build_node_fields with alert field defaults."""

    def test_with_none_returns_defaults(self) -> None:
        """Test that passing None returns all default fields."""
        result = build_node_fields(None, DEFAULT_ALERT_FIELDS)

        # Should contain all default fields
        for field in DEFAULT_ALERT_FIELDS:
            assert field in result

        # Should have proper indentation
        assert "                id" in result

    def test_with_minimal_fields(self) -> None:
        """Test building query with minimal fields."""
        result = build_node_fields(["id"], DEFAULT_ALERT_FIELDS)

        assert "                id" in result
        assert "severity" not in result
        assert "status" not in result

    def test_with_custom_fields(self) -> None:
        """Test building query with custom field selection."""
        custom_fields = ["id", "severity", "status", "name"]
        result = build_node_fields(custom_fields, DEFAULT_ALERT_FIELDS)

        for field in custom_fields:
            assert field in result

        # Should not contain other fields
        assert "description" not in result
        assert "detectedAt" not in result

    def test_with_nested_objects(self) -> None:
        """Test that nested object fields are included correctly."""
        fields = ["id", "asset { id name type }"]
        result = build_node_fields(fields, DEFAULT_ALERT_FIELDS)

        assert "id" in result
        assert "asset { id name type }" in result


class TestAlertsAutoExpansion:
    """Test auto-expansion of nested objects for alerts."""

    def test_auto_expand_asset(self) -> None:
        """Test that 'asset' expands to full fragment."""
        result = build_node_fields(["id", "asset"], DEFAULT_ALERT_FIELDS)

        assert "                id" in result
        assert "                asset { id name type }" in result
        # Should not contain just "asset" alone
        lines = result.split("\n")
        assert "                asset" not in lines

    def test_auto_expand_assignee(self) -> None:
        """Test that 'assignee' expands to full fragment (no id in alerts API)."""
        result = build_node_fields(["id", "assignee"], DEFAULT_ALERT_FIELDS)

        assert "                id" in result
        # Assignee in alerts API uses userId (not id), so no auto-prepend
        assert "                assignee { userId email fullName }" in result

    def test_auto_expand_detection_source(self) -> None:
        """Test that 'detectionSource' expands to full fragment."""
        result = build_node_fields(["id", "detectionSource"], DEFAULT_ALERT_FIELDS)

        assert "                id" in result
        assert "                detectionSource { product vendor }" in result

    def test_explicit_fragment_not_expanded(self) -> None:
        """Test that explicit fragments are used as-is, not expanded."""
        # Request only asset.id using explicit fragment
        result = build_node_fields(["id", "asset { id }"], DEFAULT_ALERT_FIELDS)

        assert "                id" in result
        assert "                asset { id }" in result
        # Should NOT expand to the full default
        assert "asset { id name type }" not in result

    def test_mixed_simple_and_nested_fields(self) -> None:
        """Test mixing simple fields with auto-expanded nested fields."""
        result = build_node_fields(["id", "severity", "asset", "status"], DEFAULT_ALERT_FIELDS)

        assert "                id" in result
        assert "                severity" in result
        assert "                asset { id name type }" in result
        assert "                status" in result

    def test_multiple_nested_objects_auto_expand(self) -> None:
        """Test multiple nested objects can be auto-expanded together."""
        result = build_node_fields(
            ["id", "asset", "assignee", "detectionSource"], DEFAULT_ALERT_FIELDS
        )

        assert "                asset { id name type }" in result
        # Assignee in alerts API uses userId (not id), so no auto-prepend
        assert "                assignee { userId email fullName }" in result
        # detectionSource doesn't have id in the schema, so no id prepended
        assert "                detectionSource { product vendor }" in result


class TestAlertsDataSourcesHandling:
    """Test special handling of dataSources field for alerts."""

    def test_data_sources_field_allowed(self) -> None:
        """Test that dataSources field is in the allowlist and can be requested."""
        # dataSources is in the allowlist for custom field selection
        result = build_node_fields(["id", "dataSources"], ALLOWED_ALERT_FIELDS)

        assert "                id" in result
        assert "                dataSources" in result

    def test_data_sources_not_in_defaults(self) -> None:
        """Test that dataSources is NOT in DEFAULT_ALERT_FIELDS to avoid conflicts."""
        # dataSources should NOT be in default fields because it's added via template substitution
        assert "dataSources" not in DEFAULT_ALERT_FIELDS
        field_string = " ".join(DEFAULT_ALERT_FIELDS)
        assert "dataSources" not in field_string

    def test_data_sources_in_allowlist(self) -> None:
        """Test that dataSources IS in ALLOWED_ALERT_FIELDS for custom field selection."""
        assert "dataSources" in ALLOWED_ALERT_FIELDS
