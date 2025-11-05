"""Unit tests for nested fragment validation in graphql_utils.

Tests the _validate_nested_fragment parser that supports arbitrary nesting depth.
"""

import pytest

from purple_mcp.libs.graphql_utils import build_node_fields


class TestValidNestedFragments:
    """Test that valid nested fragments are accepted."""

    def test_single_level_fragment(self) -> None:
        """Test basic single-level nested fragment."""
        # This should work - simple nested fragment
        default_fields = ["id", "asset { id name type }"]
        result = build_node_fields(["id", "asset { id name }"], default_fields)
        assert "asset { id name }" in result

    def test_double_nested_fragment(self) -> None:
        """Test two-level nested fragment with auto-id prepending."""
        # scope does NOT have id, but account and site do
        default_fields = ["id", "scope { account { id name } site { id name } }"]
        result = build_node_fields(
            ["id", "scope { account { id } site { name } }"], default_fields
        )
        # id is prepended to site (account already has it), but NOT to scope
        assert "scope { account { id } site { id name } }" in result

    def test_deep_nested_fragment(self) -> None:
        """Test deeply nested fragment with objects that don't have id fields."""
        # asset has id, but cloudInfo does NOT have an id field
        default_fields = [
            "id",
            "asset { id name cloudInfo { accountId region } kubernetesInfo { cluster } }",
        ]
        result = build_node_fields(
            ["id", "asset { cloudInfo { accountId region } }"], default_fields
        )
        # id is prepended to asset but NOT to cloudInfo (cloudInfo has no id field)
        assert "asset { id cloudInfo { accountId region } }" in result

    def test_mixed_nesting_fragment(self) -> None:
        """Test fragment with mix of simple and nested fields."""
        # cnapp does NOT have id, but policy does
        default_fields = [
            "id",
            "cnapp { policy { id version group } verifiedExploitable }",
        ]
        result = build_node_fields(
            ["id", "cnapp { policy { id } verifiedExploitable }"], default_fields
        )
        # id is NOT prepended to cnapp (policy already has id)
        assert "cnapp { policy { id } verifiedExploitable }" in result

    def test_multiple_siblings_at_same_level(self) -> None:
        """Test multiple sibling nested objects at the same level."""
        # scope does NOT have id, but account, site, and group do
        default_fields = ["id", "scope { account { id } site { id } group { id } }"]
        result = build_node_fields(["id", "scope { account { id } group { id } }"], default_fields)
        # id is NOT prepended to scope (account and group already have id)
        assert "scope { account { id } group { id } }" in result


class TestInvalidNestedFragments:
    """Test that invalid nested fragments are rejected."""

    def test_unbalanced_braces_too_many_open(self) -> None:
        """Test that unbalanced braces (too many opening) are rejected."""
        default_fields = ["id", "asset { id name }"]
        with pytest.raises(ValueError, match="invalid format"):
            build_node_fields(["id", "asset { { id }"], default_fields)

    def test_unbalanced_braces_too_many_close(self) -> None:
        """Test that unbalanced braces (too many closing) are rejected."""
        default_fields = ["id", "asset { id name }"]
        with pytest.raises(ValueError, match="invalid format"):
            build_node_fields(["id", "asset { id } }"], default_fields)

    def test_invalid_field_name_in_fragment(self) -> None:
        """Test that invalid field names in fragments are rejected."""
        default_fields = ["id", "asset { id name }"]
        with pytest.raises(ValueError, match="invalid format"):
            build_node_fields(["id", "asset { 123invalid }"], default_fields)

    def test_empty_fragment(self) -> None:
        """Test that empty fragments are rejected."""
        default_fields = ["id", "asset { id name }"]
        with pytest.raises(ValueError, match="invalid format"):
            build_node_fields(["id", "asset { }"], default_fields)

    def test_invalid_root_field_name(self) -> None:
        """Test that invalid root field names are rejected."""
        default_fields = ["id", "asset { id name }"]
        with pytest.raises(ValueError, match="invalid format"):
            build_node_fields(["id", "123invalid { id }"], default_fields)

    def test_unknown_nested_object_root(self) -> None:
        """Test that unknown nested object roots are rejected."""
        default_fields = ["id", "asset { id name }"]
        with pytest.raises(ValueError, match="not valid"):
            build_node_fields(["id", "unknown { id }"], default_fields)


class TestNestedFragmentBackwardCompatibility:
    """Test backward compatibility with existing test cases."""

    def test_alerts_partial_asset_fragment(self) -> None:
        """Test alerts with partial asset fragment."""
        default_fields = [
            "id",
            "severity",
            "asset { id name type }",
        ]
        fields = ["id", "severity", "asset { id name }"]
        result = build_node_fields(fields, default_fields)

        assert "id" in result
        assert "severity" in result
        assert "asset { id name }" in result

    def test_misconfigurations_partial_asset_fragment(self) -> None:
        """Test misconfigurations with partial asset fragment."""
        default_fields = [
            "id",
            "severity",
            "asset { id name type cloudInfo { accountId } }",
        ]
        fields = ["id", "severity", "asset { id name type }"]
        result = build_node_fields(fields, default_fields)

        assert "id" in result
        assert "severity" in result
        assert "asset { id name type }" in result

    def test_vulnerabilities_custom_asset_fields(self) -> None:
        """Test vulnerabilities with custom asset field selection."""
        default_fields = [
            "id",
            "asset { id name domain privileged cloudInfo { accountId region } }",
        ]
        fields = ["id", "asset { id name domain privileged }"]
        result = build_node_fields(fields, default_fields)

        assert "id" in result
        assert "asset { id name domain privileged }" in result


class TestRealWorldNestedFragments:
    """Test real-world nested fragment patterns from default fields."""

    def test_scope_fragment_from_misconfigurations(self) -> None:
        """Test scope fragment pattern from misconfigurations with auto-id prepending."""
        # scope does NOT have id, but account, site, and group do
        default_fields = [
            "id",
            "scope { account { id name } site { id name } group { id name } }",
        ]
        # User requests just account and site
        fields = ["id", "scope { account { id } site { name } }"]
        result = build_node_fields(fields, default_fields)

        # id is prepended to site (account already has it), but NOT to scope
        assert "scope { account { id } site { id name } }" in result

    def test_cnapp_fragment_from_misconfigurations(self) -> None:
        """Test cnapp fragment pattern from misconfigurations with auto-id prepending."""
        # cnapp does NOT have id, but policy does
        default_fields = ["id", "cnapp { policy { id version group } verifiedExploitable }"]
        # User requests just policy id
        fields = ["id", "cnapp { policy { id } }"]
        result = build_node_fields(fields, default_fields)

        # id is NOT prepended to cnapp (policy already has id)
        assert "cnapp { policy { id } }" in result

    def test_asset_with_cloudinfo_and_kubernetes(self) -> None:
        """Test asset fragment with cloudInfo (which has no id field)."""
        # asset has id, but cloudInfo does NOT have an id field
        default_fields = [
            "id",
            "asset { id name cloudInfo { accountId accountName providerName region } kubernetesInfo { cluster namespace } }",
        ]
        # User requests just cloudInfo accountId and region
        fields = ["id", "asset { cloudInfo { accountId region } }"]
        result = build_node_fields(fields, default_fields)

        # id is prepended to asset but NOT to cloudInfo (cloudInfo has no id field)
        assert "asset { id cloudInfo { accountId region } }" in result
