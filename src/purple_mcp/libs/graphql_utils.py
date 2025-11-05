"""Shared utilities for GraphQL field selection and query building.

This module provides common utilities used across multiple GraphQL client libraries
(alerts, misconfigurations, vulnerabilities) to build dynamic field selections with
injection protection and nested object auto-expansion.
"""

import functools
import re

from pydantic import BaseModel, Field

# Indentation for GraphQL query fields (16 spaces to align with query structure)
INDENT = " " * 16

_SIMPLE_FIELD_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class GraphQLFieldCatalog(BaseModel):
    """Unified field configuration metadata for GraphQL libraries.

    This class encapsulates all field selection metadata for a GraphQL API:
    - Default fields (used when no custom selection is provided)
    - Additional allowed fields (valid for custom selection but not in defaults)
    - Auto-expansion mappings (simple names to full fragments)

    This prevents allowlists, defaults, and documentation from drifting by
    maintaining a single source of truth for field configuration.

    Attributes:
        default_fields: Fields returned when no custom selection is specified.
                       May include both simple fields and nested fragments.
        additional_allowed_fields: Fields valid for custom selection but not
                                  included in defaults (e.g., conditional fields).
        description: Optional human-readable description of this field catalog.

    Example:
        >>> catalog = GraphQLFieldCatalog(
        ...     default_fields=["id", "name", "asset { id name type }"],
        ...     additional_allowed_fields=["dataSources"],
        ... )
        >>> catalog.get_all_allowed_fields()
        ['id', 'name', 'asset { id name type }', 'dataSources']
        >>> catalog.get_nested_mappings()
        {'asset': 'asset { id name type }'}
    """

    default_fields: list[str] = Field(
        description="Default fields returned when no field selection is specified"
    )
    additional_allowed_fields: list[str] = Field(
        default_factory=list,
        description="Additional fields valid for custom selection but not in defaults",
    )
    description: str | None = Field(
        default=None, description="Human-readable description of this catalog"
    )

    def get_all_allowed_fields(self) -> list[str]:
        """Get complete allowlist of all valid fields (defaults + additional).

        Returns:
            List of all field names that are valid for custom field selection.
        """
        return [*self.default_fields, *self.additional_allowed_fields]

    def get_nested_mappings(self) -> dict[str, str]:
        """Extract nested object name to full fragment mappings.

        Returns:
            Dictionary mapping simple object names (e.g., "asset") to their
            full fragment definitions (e.g., "asset { id name type }").

        Example:
            >>> catalog = GraphQLFieldCatalog(default_fields=["id", "asset { id name }"])
            >>> catalog.get_nested_mappings()
            {'asset': 'asset { id name }'}
        """
        mappings: dict[str, str] = {}
        for field in self.get_all_allowed_fields():
            if "{" in field:
                # Extract the object name (part before the opening brace)
                object_name = field.split("{")[0].strip()
                mappings[object_name] = field
        return mappings

    model_config = {"frozen": True}  # Make immutable for safety


_FIELD_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_nested_fragment(fragment: str) -> bool:  # noqa: C901
    """Validate a nested field fragment with arbitrary nesting depth.

    This parser validates GraphQL fragment syntax with the following rules:
    - Root must be a valid field name followed by opening brace
    - Contents can be simple field names or nested fragments
    - All braces must be balanced and properly nested
    - Field names must match GraphQL identifier rules

    Args:
        fragment: The fragment string to validate (e.g., "asset { id name }")

    Returns:
        True if the fragment is valid, False otherwise.

    Examples:
        >>> _validate_nested_fragment("asset { id name }")
        True
        >>> _validate_nested_fragment("asset { cloudInfo { accountId } }")
        True
        >>> _validate_nested_fragment("scope { account { id } site { name } }")
        True
        >>> _validate_nested_fragment("invalid { { }")
        False
    """
    if "{" not in fragment:
        return False

    parts = fragment.split("{", 1)
    if len(parts) != 2:
        return False

    root_field = parts[0].strip()
    if not _FIELD_NAME_PATTERN.match(root_field):
        return False

    content = parts[1]

    tokens: list[str] = []
    current_token = ""

    for char in content:
        if char in "{}" or char.isspace():
            if current_token:
                tokens.append(current_token)
                current_token = ""
            if char in "{}":
                tokens.append(char)
        else:
            current_token += char

    if current_token:
        tokens.append(current_token)

    brace_count = 1
    i = 0
    has_fields = False

    while i < len(tokens):
        token = tokens[i]

        if token == "{":
            brace_count += 1
            if i == 0 or not _FIELD_NAME_PATTERN.match(tokens[i - 1]):
                return False
        elif token == "}":
            brace_count -= 1
            if brace_count < 0:
                return False
        else:
            if not _FIELD_NAME_PATTERN.match(token):
                return False
            has_fields = True

        i += 1

    return brace_count == 0 and has_fields


@functools.lru_cache(maxsize=8)
def _get_nested_mappings(fields_tuple: tuple[str, ...]) -> dict[str, str]:
    """Extract nested object name to full fragment mappings from default fields (cached).

    This enables auto-expansion of simple nested object names (e.g., "asset")
    to their full fragment definitions (e.g., "asset { id name type }").

    Uses LRU cache to avoid repeated parsing of the same field lists across calls.

    Args:
        fields_tuple: Tuple of default field definitions (tuple for hashability).

    Returns:
        Dictionary mapping simple object names to their full fragments.

    Example:
        >>> fields = ("id", "asset { id name type }", "cve { id score }")
        >>> _get_nested_mappings(fields)
        {'asset': 'asset { id name type }', 'cve': 'cve { id score }'}
    """
    mappings: dict[str, str] = {}
    for field in fields_tuple:
        if "{" in field:
            # Extract the object name (part before the opening brace)
            object_name = field.split("{")[0].strip()
            mappings[object_name] = field
    return mappings


def _ensure_id_in_fragment(fragment: str) -> str:  # noqa: C901
    """Ensure 'id' field is present at each nesting level in a fragment.

    Automatically prepends 'id' to nested fragments if not already present,
    ensuring Pydantic models can validate responses correctly.

    Only prepends id for objects that have id fields in the GraphQL schema.
    Objects without id fields (like CloudInfo, KubernetesInfo) are left unchanged.

    Args:
        fragment: A nested fragment like "asset { name }" or "scope { account { name } }"

    Returns:
        Fragment with 'id' prepended at each level if not present (for objects with ids).

    Examples:
        >>> _ensure_id_in_fragment("asset { name }")
        "asset { id name }"
        >>> _ensure_id_in_fragment("asset { id name }")
        "asset { id name }"
        >>> _ensure_id_in_fragment("scope { account { name } }")
        "scope { id account { id name } }"
        >>> _ensure_id_in_fragment("asset { cloudInfo { region } }")
        "asset { id cloudInfo { region } }"
    """
    objects_with_id = {
        "asset",
        "account",
        "site",
        "group",
        "cve",
        "policy",
        "admissionRequest",
    }

    if "{" not in fragment:
        return fragment

    parts = fragment.split("{", 1)
    root_field = parts[0].strip()
    remaining = parts[1]

    tokens = []
    current_token = ""
    brace_depth = 0
    i = 0

    while i < len(remaining):
        char = remaining[i]

        if char == "{":
            brace_depth += 1
            current_token += char
        elif char == "}":
            if brace_depth > 0:
                brace_depth -= 1
                current_token += char
            else:
                if current_token:
                    tokens.append(current_token.strip())
                break
        elif char.isspace() and brace_depth == 0:
            peek_ahead = remaining[i + 1 :].lstrip()
            if peek_ahead.startswith("{"):
                current_token += char
            elif current_token:
                tokens.append(current_token.strip())
                current_token = ""
        else:
            current_token += char

        i += 1

    if current_token and brace_depth == 0:
        tokens.append(current_token.strip())

    has_id = False
    processed_tokens = []

    for token in tokens:
        if token == "id":
            has_id = True
            processed_tokens.append(token)
        elif "{" in token:
            processed_tokens.append(_ensure_id_in_fragment(token))
        else:
            processed_tokens.append(token)

    if not has_id and root_field.lower() in objects_with_id:
        processed_tokens.insert(0, "id")

    return f"{root_field} {{ {' '.join(processed_tokens)} }}"


def _validate_field_name(
    field: str, allowed_fields: set[str], nested_mappings: dict[str, str]
) -> None:
    """Validate a single field name against GraphQL injection attacks.

    Args:
        field: The field name to validate.
        allowed_fields: Set of allowed field names and patterns.
        nested_mappings: Dictionary mapping simple nested object names to full fragments.

    Raises:
        ValueError: If the field name is invalid or contains suspicious characters.
    """
    field = field.strip()

    if not field:
        raise ValueError("Empty field name is not allowed")

    if field in allowed_fields:
        return

    if field in nested_mappings:
        return

    if "{" in field:
        if not _validate_nested_fragment(field):
            raise ValueError(
                f"Nested field '{field}' has invalid format. "
                "Must follow GraphQL fragment syntax with balanced braces and valid field names. "
                "Examples: 'asset {{ id name }}', 'scope {{ account {{ id }} site {{ name }} }}'"
            )

        root_field = field.split("{")[0].strip()
        if root_field not in nested_mappings:
            raise ValueError(
                f"Nested object '{root_field}' is not valid. "
                f"Valid nested objects are: {sorted(nested_mappings.keys())}"
            )

        return

    suspicious_chars = ["...", "@", "#", "(", ")", "[", "]", "$", "!"]
    for char in suspicious_chars:
        if char in field:
            raise ValueError(
                f"Field name '{field}' contains suspicious character '{char}' "
                "that could be used for GraphQL injection"
            )

    if _SIMPLE_FIELD_PATTERN.match(field):
        raise ValueError(
            f"Field name '{field}' is not in the allowlist of valid fields. "
            f"Valid fields are: {sorted(allowed_fields)}"
        )

    raise ValueError(
        f"Field name '{field}' has invalid format. "
        "Field names must be alphanumeric identifiers or valid nested field patterns."
    )


def build_node_fields(
    fields: list[str] | None, default_fields: list[str] | GraphQLFieldCatalog
) -> str:
    r"""Build GraphQL node field selection string with injection protection and auto-expansion.

    This function supports two syntaxes for nested objects:
    1. Simple name (e.g., "asset") - automatically expands to full fragment
    2. Full fragment (e.g., "asset { id name type }") - uses as-is

    Args:
        fields: List of field names to include, or None for all fields.
               Supports simple nested object names (e.g., "asset") which will be
               auto-expanded to their default fragments (e.g., "asset { id name type }").
               Empty list is coerced to ["id"] to ensure valid GraphQL.
               The "id" field is always automatically included if not present.
        default_fields: Default field list (or GraphQLFieldCatalog) to use when
                       fields is None. If a catalog is provided, its default_fields
                       will be used, and custom fields will be validated against
                       the complete allowlist.

    Returns:
        Indented string of field names for GraphQL query.

    Raises:
        ValueError: If any field name is invalid or contains suspicious characters.

    Examples:
        >>> # Simple fields
        >>> build_node_fields(["id", "severity"], default_fields)
        "                id\n                severity"

        >>> # id is automatically prepended if not present
        >>> build_node_fields(["severity"], default_fields)
        "                id\n                severity"

        >>> # Auto-expansion of nested objects
        >>> build_node_fields(["id", "asset"], default_fields)
        "                id\n                asset { id name type }"

        >>> # Explicit nested fragments also work
        >>> build_node_fields(["id", "asset { id }"], default_fields)
        "                id\n                asset { id }"

        >>> # Empty list is coerced to ["id"]
        >>> build_node_fields([], default_fields)
        "                id"

        >>> # Using GraphQLFieldCatalog
        >>> catalog = GraphQLFieldCatalog(default_fields=["id", "name"])
        >>> build_node_fields(None, catalog)
        "                id\n                name"
    """
    if isinstance(default_fields, GraphQLFieldCatalog):
        defaults_list = default_fields.default_fields
        allowed_list = default_fields.get_all_allowed_fields()
        nested_mappings = default_fields.get_nested_mappings()
    else:
        defaults_list = default_fields
        allowed_list = default_fields
        nested_mappings = _get_nested_mappings(tuple(default_fields))

    field_list = fields if fields is not None else defaults_list

    if fields is None:
        return "\n".join(f"{INDENT}{field}" for field in field_list)

    if len(field_list) == 0:
        field_list = ["id"]

    if "id" not in field_list:
        field_list = ["id", *list(field_list)]

    allowed_fields_set = set(allowed_list)

    expanded_fields: list[str] = []
    for field in field_list:
        _validate_field_name(field, allowed_fields_set, nested_mappings)

        if field in nested_mappings:
            expanded = nested_mappings[field]
            expanded_fields.append(_ensure_id_in_fragment(expanded))
        elif "{" in field:
            expanded_fields.append(_ensure_id_in_fragment(field))
        else:
            expanded_fields.append(field)

    return "\n".join(f"{INDENT}{field}" for field in expanded_fields)
