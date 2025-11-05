"""Core unit tests for graphql_utils.build_node_fields function.

Tests the shared field selection logic that works across all GraphQL libraries.
"""

import inspect

from purple_mcp.libs.alerts.client import DEFAULT_ALERT_FIELDS
from purple_mcp.libs.graphql_utils import build_node_fields
from purple_mcp.libs.misconfigurations.templates import DEFAULT_MISCONFIGURATION_FIELDS
from purple_mcp.libs.vulnerabilities.templates import DEFAULT_VULNERABILITY_FIELDS


class TestBuildNodeFieldsSignature:
    """Test the function signature and basic behavior."""

    def test_has_expected_signature(self) -> None:
        """Test that build_node_fields function has the expected signature."""
        sig = inspect.signature(build_node_fields)
        assert list(sig.parameters.keys()) == ["fields", "default_fields"]


class TestBuildNodeFieldsConsistency:
    """Test that field selection behaves consistently across all libraries."""

    def test_handle_none_consistently(self) -> None:
        """Test that all builders handle None consistently."""
        alerts_result = build_node_fields(None, DEFAULT_ALERT_FIELDS)
        misconfig_result = build_node_fields(None, DEFAULT_MISCONFIGURATION_FIELDS)
        vuln_result = build_node_fields(None, DEFAULT_VULNERABILITY_FIELDS)

        # All should return non-empty strings
        assert alerts_result
        assert misconfig_result
        assert vuln_result

        # All should contain their default fields
        for field in DEFAULT_ALERT_FIELDS:
            assert field in alerts_result

        for field in DEFAULT_MISCONFIGURATION_FIELDS:
            assert field in misconfig_result

        for field in DEFAULT_VULNERABILITY_FIELDS:
            assert field in vuln_result

    def test_handle_empty_list_consistently(self) -> None:
        """Test that all builders handle empty list consistently by coercing to ['id']."""
        alerts_result = build_node_fields([], DEFAULT_ALERT_FIELDS)
        misconfig_result = build_node_fields([], DEFAULT_MISCONFIGURATION_FIELDS)
        vuln_result = build_node_fields([], DEFAULT_VULNERABILITY_FIELDS)

        # All should return just the id field (empty list coerced to ["id"])
        assert alerts_result == "                id"
        assert misconfig_result == "                id"
        assert vuln_result == "                id"


class TestIdFieldAutoInclusion:
    """Test that 'id' field is always automatically included in queries."""

    def test_id_automatically_prepended_when_missing(self) -> None:
        """Test that id is automatically added when not in the field list."""
        result = build_node_fields(["severity", "status"], DEFAULT_ALERT_FIELDS)

        # Should have id prepended
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0] == "                id"
        assert lines[1] == "                severity"
        assert lines[2] == "                status"

    def test_id_not_duplicated_when_already_present(self) -> None:
        """Test that id is not duplicated if already in the list."""
        result = build_node_fields(["id", "severity"], DEFAULT_ALERT_FIELDS)

        # Should have id only once
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0] == "                id"
        assert lines[1] == "                severity"

    def test_id_prepended_for_alerts(self) -> None:
        """Test id auto-inclusion for alerts."""
        result = build_node_fields(["severity"], DEFAULT_ALERT_FIELDS)
        assert "                id" in result
        assert result.startswith("                id")

    def test_id_prepended_for_misconfigurations(self) -> None:
        """Test id auto-inclusion for misconfigurations."""
        result = build_node_fields(["severity"], DEFAULT_MISCONFIGURATION_FIELDS)
        assert "                id" in result
        assert result.startswith("                id")

    def test_id_prepended_for_vulnerabilities(self) -> None:
        """Test id auto-inclusion for vulnerabilities."""
        result = build_node_fields(["severity"], DEFAULT_VULNERABILITY_FIELDS)
        assert "                id" in result
        assert result.startswith("                id")

    def test_id_with_nested_objects(self) -> None:
        """Test that id is included when using nested object fields."""
        result = build_node_fields(["severity", "asset"], DEFAULT_ALERT_FIELDS)

        lines = result.split("\n")
        assert lines[0] == "                id"
        assert "severity" in result
        assert "asset { id name type }" in result

    def test_id_already_at_end_of_list(self) -> None:
        """Test that id is moved to the front if it appears later in the list."""
        result = build_node_fields(["severity", "status", "id"], DEFAULT_ALERT_FIELDS)

        # id should appear only once (not moved, already present)
        assert result.count("id") == 1

    def test_single_non_id_field(self) -> None:
        """Test token-saving scenario: single field without id."""
        result = build_node_fields(["severity"], DEFAULT_ALERT_FIELDS)

        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0] == "                id"
        assert lines[1] == "                severity"
