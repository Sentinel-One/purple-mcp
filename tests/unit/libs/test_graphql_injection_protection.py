"""Unit tests for GraphQL injection protection across all libraries.

This module tests the validation logic added to prevent GraphQL injection attacks
in the build_node_fields function used by alerts, misconfigurations, and vulnerabilities.
"""

from collections.abc import Callable

import pytest

from purple_mcp.libs.alerts.client import DEFAULT_ALERT_FIELDS
from purple_mcp.libs.graphql_utils import build_node_fields
from purple_mcp.libs.misconfigurations.templates import DEFAULT_MISCONFIGURATION_FIELDS
from purple_mcp.libs.vulnerabilities.templates import DEFAULT_VULNERABILITY_FIELDS


class TestAlertsGraphQLInjectionProtection:
    """Test GraphQL injection protection for alerts library."""

    def test_valid_simple_fields(self) -> None:
        """Test that valid simple field names are accepted."""
        valid_fields = ["id", "severity", "status"]
        result = build_node_fields(valid_fields, DEFAULT_ALERT_FIELDS)
        assert "id" in result
        assert "severity" in result
        assert "status" in result

    def test_valid_nested_fields(self) -> None:
        """Test that valid nested field structures are accepted."""
        valid_fields = ["id", "asset { id name type }"]
        result = build_node_fields(valid_fields, DEFAULT_ALERT_FIELDS)
        assert "id" in result
        assert "asset { id name type }" in result

    def test_default_fields_bypass_validation(self) -> None:
        """Test that default fields bypass validation (None fields parameter)."""
        result = build_node_fields(None, DEFAULT_ALERT_FIELDS)
        assert "id" in result
        assert len(result) > 0

    def test_injection_with_closing_brace(self) -> None:
        """Test that fields containing closing braces are rejected."""
        malicious_fields = ["id", "} } __schema { types { name } } ... on Alert { id"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        # Should be rejected (either invalid format or suspicious character)
        error_msg = str(exc_info.value).lower()
        assert "invalid format" in error_msg or "suspicious character" in error_msg

    def test_injection_with_opening_brace(self) -> None:
        """Test that fields containing opening braces (not in allowlist) are rejected."""
        malicious_fields = ["id { __schema { types { name } } }"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        # Should be rejected (either invalid format or not valid)
        error_msg = str(exc_info.value).lower()
        assert "invalid format" in error_msg or "not valid" in error_msg

    def test_injection_with_fragment(self) -> None:
        """Test that fields containing fragment syntax are rejected."""
        malicious_fields = ["id", "... on Alert { __schema { types { name } } }"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        # Should be rejected (either invalid format or suspicious character)
        error_msg = str(exc_info.value).lower()
        assert "invalid format" in error_msg or "suspicious character" in error_msg

    def test_injection_with_directive(self) -> None:
        """Test that fields containing directive syntax are rejected."""
        malicious_fields = ["id", "@include(if: true) { __schema }"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        # Should be rejected (either invalid format or suspicious character)
        error_msg = str(exc_info.value).lower()
        assert "invalid format" in error_msg or "suspicious character" in error_msg

    def test_injection_with_parentheses(self) -> None:
        """Test that fields containing parentheses are rejected."""
        malicious_fields = ["id", "severity(if: true)"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        assert "suspicious character" in str(exc_info.value).lower()
        assert "(" in str(exc_info.value) or ")" in str(exc_info.value)

    def test_injection_with_dollar_sign(self) -> None:
        """Test that fields containing dollar signs are rejected."""
        malicious_fields = ["id", "$variable"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        assert "suspicious character" in str(exc_info.value).lower()
        assert "$" in str(exc_info.value)

    def test_injection_with_brackets(self) -> None:
        """Test that fields containing brackets are rejected."""
        malicious_fields = ["id", "items[0]"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        assert "suspicious character" in str(exc_info.value).lower()

    def test_field_not_in_allowlist(self) -> None:
        """Test that fields not in the allowlist are rejected."""
        invalid_fields = ["id", "maliciousField"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(invalid_fields, DEFAULT_ALERT_FIELDS)
        assert "not in the allowlist" in str(exc_info.value).lower()
        assert "maliciousField" in str(exc_info.value)

    def test_empty_field_name(self) -> None:
        """Test that empty field names are rejected."""
        invalid_fields = ["id", ""]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(invalid_fields, DEFAULT_ALERT_FIELDS)
        assert "empty field name" in str(exc_info.value).lower()

    def test_whitespace_only_field(self) -> None:
        """Test that whitespace-only fields are rejected."""
        invalid_fields = ["id", "   "]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(invalid_fields, DEFAULT_ALERT_FIELDS)
        assert "empty field name" in str(exc_info.value).lower()

    def test_schema_introspection_injection(self) -> None:
        """Test that schema introspection injection attempts are blocked."""
        malicious_fields = ["id", "__schema"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        assert "not in the allowlist" in str(exc_info.value).lower()

    def test_typename_injection(self) -> None:
        """Test that __typename injection attempts are blocked."""
        malicious_fields = ["id", "__typename"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_ALERT_FIELDS)
        assert "not in the allowlist" in str(exc_info.value).lower()


class TestMisconfigurationsGraphQLInjectionProtection:
    """Test GraphQL injection protection for misconfigurations library."""

    def test_valid_simple_fields(self) -> None:
        """Test that valid simple field names are accepted."""
        valid_fields = ["id", "severity", "status"]
        result = build_node_fields(valid_fields, DEFAULT_MISCONFIGURATION_FIELDS)
        assert "id" in result
        assert "severity" in result
        assert "status" in result

    def test_valid_nested_fields(self) -> None:
        """Test that valid nested field structures are accepted."""
        valid_fields = ["id", "assignee { id email fullName }"]
        result = build_node_fields(valid_fields, DEFAULT_MISCONFIGURATION_FIELDS)
        assert "id" in result
        assert "assignee { id email fullName }" in result

    def test_injection_with_closing_brace(self) -> None:
        """Test that fields containing closing braces are rejected."""
        malicious_fields = ["id", "} } __schema { types { name } }"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_MISCONFIGURATION_FIELDS)
        # Should be rejected (either invalid format or suspicious character)
        error_msg = str(exc_info.value).lower()
        assert "invalid format" in error_msg or "suspicious character" in error_msg

    def test_field_not_in_allowlist(self) -> None:
        """Test that fields not in the allowlist are rejected."""
        invalid_fields = ["id", "unknownField"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(invalid_fields, DEFAULT_MISCONFIGURATION_FIELDS)
        assert "not in the allowlist" in str(exc_info.value).lower()

    def test_complex_nested_injection(self) -> None:
        """Test complex nested injection attempt."""
        # Try to inject a nested object that's not in the allowlist
        malicious_fields = ["id", "malicious { __schema { types } }"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_MISCONFIGURATION_FIELDS)
        # Should be rejected (either invalid format or not valid)
        error_msg = str(exc_info.value).lower()
        assert "invalid format" in error_msg or "not valid" in error_msg


class TestVulnerabilitiesGraphQLInjectionProtection:
    """Test GraphQL injection protection for vulnerabilities library."""

    def test_valid_simple_fields(self) -> None:
        """Test that valid simple field names are accepted."""
        valid_fields = ["id", "name", "severity"]
        result = build_node_fields(valid_fields, DEFAULT_VULNERABILITY_FIELDS)
        assert "id" in result
        assert "name" in result
        assert "severity" in result

    def test_valid_nested_fields(self) -> None:
        """Test that valid nested field structures are accepted."""
        # software does NOT have an id field in the schema, so id will NOT be auto-prepended
        valid_fields = ["id", "software { name version fixVersion type vendor }"]
        result = build_node_fields(valid_fields, DEFAULT_VULNERABILITY_FIELDS)
        assert "id" in result
        assert "software { name version fixVersion type vendor }" in result

    def test_injection_with_closing_brace(self) -> None:
        """Test that fields containing closing braces are rejected."""
        malicious_fields = ["id", "} __schema { types { name } }"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(malicious_fields, DEFAULT_VULNERABILITY_FIELDS)
        # Should be rejected (either invalid format or suspicious character)
        error_msg = str(exc_info.value).lower()
        assert "invalid format" in error_msg or "suspicious character" in error_msg

    def test_field_not_in_allowlist(self) -> None:
        """Test that fields not in the allowlist are rejected."""
        invalid_fields = ["id", "invalidField"]
        with pytest.raises(ValueError) as exc_info:
            build_node_fields(invalid_fields, DEFAULT_VULNERABILITY_FIELDS)
        assert "not in the allowlist" in str(exc_info.value).lower()

    def test_default_fields_bypass_validation(self) -> None:
        """Test that default fields bypass validation (None fields parameter)."""
        result = build_node_fields(None, DEFAULT_VULNERABILITY_FIELDS)
        assert "id" in result
        assert len(result) > 0


class TestCrossLibraryConsistency:
    """Test that all three libraries have consistent security protection."""

    @pytest.mark.parametrize(
        "build_func,default_fields",
        [
            (build_node_fields, DEFAULT_ALERT_FIELDS),
            (build_node_fields, DEFAULT_MISCONFIGURATION_FIELDS),
            (build_node_fields, DEFAULT_VULNERABILITY_FIELDS),
        ],
    )
    def test_all_libraries_reject_schema_introspection(
        self,
        build_func: Callable[[list[str] | None, list[str]], str],
        default_fields: list[str],
    ) -> None:
        """Test that all libraries reject schema introspection."""
        malicious_fields = ["id", "__schema"]
        with pytest.raises(ValueError):
            build_func(malicious_fields, default_fields)

    @pytest.mark.parametrize(
        "build_func,default_fields",
        [
            (build_node_fields, DEFAULT_ALERT_FIELDS),
            (build_node_fields, DEFAULT_MISCONFIGURATION_FIELDS),
            (build_node_fields, DEFAULT_VULNERABILITY_FIELDS),
        ],
    )
    def test_all_libraries_reject_fragment_injection(
        self,
        build_func: Callable[[list[str] | None, list[str]], str],
        default_fields: list[str],
    ) -> None:
        """Test that all libraries reject fragment injection."""
        malicious_fields = ["id", "... on Query { __schema }"]
        with pytest.raises(ValueError):
            build_func(malicious_fields, default_fields)

    @pytest.mark.parametrize(
        "build_func,default_fields",
        [
            (build_node_fields, DEFAULT_ALERT_FIELDS),
            (build_node_fields, DEFAULT_MISCONFIGURATION_FIELDS),
            (build_node_fields, DEFAULT_VULNERABILITY_FIELDS),
        ],
    )
    def test_all_libraries_reject_directive_injection(
        self,
        build_func: Callable[[list[str] | None, list[str]], str],
        default_fields: list[str],
    ) -> None:
        """Test that all libraries reject directive injection."""
        malicious_fields = ["id", "@skip(if: true) { malicious }"]
        with pytest.raises(ValueError):
            build_func(malicious_fields, default_fields)

    @pytest.mark.parametrize(
        "build_func,default_fields",
        [
            (build_node_fields, DEFAULT_ALERT_FIELDS),
            (build_node_fields, DEFAULT_MISCONFIGURATION_FIELDS),
            (build_node_fields, DEFAULT_VULNERABILITY_FIELDS),
        ],
    )
    def test_all_libraries_accept_valid_fields(
        self,
        build_func: Callable[[list[str] | None, list[str]], str],
        default_fields: list[str],
    ) -> None:
        """Test that all libraries accept valid fields."""
        valid_fields = ["id"]
        result = build_func(valid_fields, default_fields)
        assert "id" in result
