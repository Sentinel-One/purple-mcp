"""Unit tests for inventory tool fetch_fields parameter parsing."""

import pytest

from purple_mcp.libs.inventory.field_presets import InventoryFetchFieldsPreset
from purple_mcp.tools.inventory import _parse_fetch_fields


class TestParseFetchFields:
    """Test _parse_fetch_fields helper function."""

    @pytest.mark.parametrize(
        "preset_name",
        ["MINIMAL", "minimal", "Minimal", "MiNiMaL"],
    )
    def test_parse_minimal_preset_case_insensitive(self, preset_name: str) -> None:
        """Test MINIMAL preset name parsing (case-insensitive)."""
        result = _parse_fetch_fields(preset_name)
        assert result == set(InventoryFetchFieldsPreset.MINIMAL.value)

    @pytest.mark.parametrize(
        "preset_name",
        ["STANDARD", "standard", "Standard", "StAnDaRd"],
    )
    def test_parse_standard_preset_case_insensitive(self, preset_name: str) -> None:
        """Test STANDARD preset name parsing (case-insensitive)."""
        result = _parse_fetch_fields(preset_name)
        assert result == set(InventoryFetchFieldsPreset.STANDARD.value)

    @pytest.mark.parametrize(
        "preset_name",
        ["ALL", "all", "All", "AlL"],
    )
    def test_parse_all_preset_case_insensitive(self, preset_name: str) -> None:
        """Test ALL preset name parsing (case-insensitive)."""
        result = _parse_fetch_fields(preset_name)
        assert result == set(InventoryFetchFieldsPreset.ALL.value)

    def test_parse_invalid_preset_name(self) -> None:
        """Test that invalid preset name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            _parse_fetch_fields("INVALID_PRESET")

        error_msg = str(exc_info.value)
        assert "Invalid preset name" in error_msg
        assert "MINIMAL" in error_msg
        assert "STANDARD" in error_msg
        assert "ALL" in error_msg

    def test_parse_custom_field_list_valid(self) -> None:
        """Test parsing valid custom field list."""
        custom_fields = ["id", "name", "category"]
        result = _parse_fetch_fields(custom_fields)
        assert result == set(custom_fields)

    def test_parse_custom_field_list_single_field(self) -> None:
        """Test parsing custom field list with single field."""
        custom_fields = ["id"]
        result = _parse_fetch_fields(custom_fields)
        assert result == set(custom_fields)

    def test_parse_custom_field_list_empty_raises_error(self) -> None:
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            _parse_fetch_fields([])

        assert "cannot be empty" in str(exc_info.value)

    def test_parse_custom_field_list_with_invalid_field(self) -> None:
        """Test that list with invalid field names raises ValueError."""
        custom_fields = ["id", "name", "invalid_field", "another_invalid"]

        with pytest.raises(ValueError) as exc_info:
            _parse_fetch_fields(custom_fields)

        error_msg = str(exc_info.value)
        assert "Invalid field names" in error_msg
        assert "invalid_field" in error_msg
        assert "another_invalid" in error_msg
        assert "Use 'ALL' preset" in error_msg

    def test_parse_dict_iterates_over_keys(self) -> None:
        """Test that dict iterates over keys (valid field names)."""
        # Dict iteration yields keys, which should be valid field names
        result = _parse_fetch_fields({"id": "value", "name": "other"})
        assert result == {"id", "name"}

    def test_minimal_fields_are_subset_of_all_fields(self) -> None:
        """Test that MINIMAL preset fields are valid according to ALL preset."""
        minimal_fields = _parse_fetch_fields("MINIMAL")
        assert minimal_fields is not None

        all_fields_set = set(InventoryFetchFieldsPreset.ALL.value)
        for field in minimal_fields:
            assert field in all_fields_set, f"Field '{field}' not in ALL preset"

    def test_standard_fields_are_subset_of_all_fields(self) -> None:
        """Test that STANDARD preset fields are valid according to ALL preset."""
        standard_fields = _parse_fetch_fields("STANDARD")
        assert standard_fields is not None

        all_fields_set = set(InventoryFetchFieldsPreset.ALL.value)
        for field in standard_fields:
            assert field in all_fields_set, f"Field '{field}' not in ALL preset"
