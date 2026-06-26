"""Tests for threat_intelligence configuration."""

import pytest
from pydantic import ValidationError

from purple_mcp.libs.threat_intelligence import ThreatIntelligenceConfig


class TestThreatIntelligenceConfig:
    """Test ThreatIntelligenceConfig validation."""

    def test_valid_config(self) -> None:
        """Test creating a valid config."""
        config = ThreatIntelligenceConfig(
            api_key="test_api_key_12345",
            timeout=30.0,
        )
        assert config.api_key == "test_api_key_12345"
        assert config.timeout == 30.0

    def test_empty_api_key_raises_validation_error(self) -> None:
        """Test that empty api_key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatIntelligenceConfig(
                api_key="",
                timeout=30.0,
            )
        errors = exc_info.value.errors()
        assert any("api_key cannot be empty" in str(error["ctx"]["error"]) for error in errors)

    def test_whitespace_only_api_key_raises_validation_error(self) -> None:
        """Test that whitespace-only api_key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatIntelligenceConfig(
                api_key="   ",
                timeout=30.0,
            )
        errors = exc_info.value.errors()
        assert any("api_key cannot be empty" in str(error["ctx"]["error"]) for error in errors)

    def test_api_key_strips_whitespace(self) -> None:
        """Test that api_key strips leading/trailing whitespace."""
        config = ThreatIntelligenceConfig(
            api_key="  test_key  ",
            timeout=30.0,
        )
        assert config.api_key == "test_key"

    def test_zero_timeout_raises_validation_error(self) -> None:
        """Test that zero timeout raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatIntelligenceConfig(
                api_key="test_key",
                timeout=0.0,
            )
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than" for error in errors)
        assert any(error["loc"] == ("timeout",) for error in errors)

    def test_negative_timeout_raises_validation_error(self) -> None:
        """Test that negative timeout raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatIntelligenceConfig(
                api_key="test_key",
                timeout=-10.0,
            )
        errors = exc_info.value.errors()
        assert any(error["type"] == "greater_than" for error in errors)
        assert any(error["loc"] == ("timeout",) for error in errors)

    def test_missing_api_key_raises_validation_error(self) -> None:
        """Test that missing api_key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ThreatIntelligenceConfig(timeout=30.0)
        errors = exc_info.value.errors()
        assert any(error["type"] == "missing" for error in errors)
        assert any(error["loc"] == ("api_key",) for error in errors)
