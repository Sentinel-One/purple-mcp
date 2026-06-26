"""Tests for CVE configuration."""

import pytest
from pydantic import ValidationError

from purple_mcp.libs.cve import CVEConfig


class TestCVEConfig:
    """Test CVE configuration class."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CVEConfig()
        assert config.base_url == "https://cve.circl.lu/api/"
        assert config.timeout == 30.0

    def test_base_url_rejects_http(self) -> None:
        """Test that HTTP URLs are rejected."""
        with pytest.raises(ValidationError, match="base_url must use HTTPS"):
            CVEConfig(base_url="http://localhost:8000/api")

    def test_base_url_rejects_invalid_protocol(self) -> None:
        """Test that invalid protocols are rejected."""
        with pytest.raises(ValidationError, match="URL scheme should be 'http' or 'https'"):
            CVEConfig(base_url="ftp://invalid.test/api")

    def test_base_url_rejects_empty_string(self) -> None:
        """Test that empty string is rejected."""
        with pytest.raises(ValidationError, match="input is empty"):
            CVEConfig(base_url="")

    def test_timeout_rejects_negative(self) -> None:
        """Test that negative timeout is rejected."""
        with pytest.raises(ValidationError, match="Input should be greater than 0"):
            CVEConfig(timeout=-1.0)

    def test_timeout_rejects_zero(self) -> None:
        """Test that zero timeout is rejected."""
        with pytest.raises(ValidationError, match="Input should be greater than 0"):
            CVEConfig(timeout=0.0)
