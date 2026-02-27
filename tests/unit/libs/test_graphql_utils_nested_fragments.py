"""Unit tests for nested fragment validation in graphql_utils.

Tests the _validate_nested_fragment parser that supports arbitrary nesting depth.
"""

import pytest

from purple_mcp.libs.graphql_utils import (
    MAX_CUSTOM_FRAGMENT_DEPTH,
    _ensure_id_in_fragment,
    build_node_fields,
)


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


def _adjacent_closing_braces_fragment(depth: int) -> str:
    """Build a valid nested fragment without whitespace between closing braces.

    Args:
        depth: Number of nested `a { ... }` levels inside `asset { ... }`.

    Returns:
        Fragment string with adjacent closing braces between nested levels.
    """
    return "asset{" + ("a{" * depth) + "x" + ("}" * depth) + "}"


def test_adjacent_closing_braces_do_not_duplicate_tokens() -> None:
    """Token parsing should not duplicate nested fragments on root close."""
    result = _ensure_id_in_fragment("asset{a{x}}")
    assert result == "asset { id a { x } }"


def test_deep_adjacent_closing_braces_remain_bounded() -> None:
    """Deep nested fragments should remain linear in output size."""
    result = _ensure_id_in_fragment(_adjacent_closing_braces_fragment(12))
    assert len(result) < 256


def test_custom_fragment_depth_limit_allows_boundary_value() -> None:
    """Depth exactly at the configured limit should be accepted."""
    default_fields = ["id", "asset { id name }"]
    fragment = _adjacent_closing_braces_fragment(MAX_CUSTOM_FRAGMENT_DEPTH - 1)
    result = build_node_fields(["id", fragment], default_fields)
    assert "asset { id" in result


def test_custom_fragment_depth_limit_rejects_deeper_values() -> None:
    """Depth over the configured limit should be rejected."""
    default_fields = ["id", "asset { id name }"]
    fragment = _adjacent_closing_braces_fragment(MAX_CUSTOM_FRAGMENT_DEPTH)
    with pytest.raises(ValueError, match="exceeds maximum allowed depth"):
        build_node_fields(["id", fragment], default_fields)


def test_processed_fragment_output_has_hard_cap() -> None:
    """String building should reject oversized processed fragments."""
    oversized_fragment = "asset{" + " ".join("x" for _ in range(5000)) + "}"
    with pytest.raises(ValueError, match="output is too large"):
        _ensure_id_in_fragment(oversized_fragment)
