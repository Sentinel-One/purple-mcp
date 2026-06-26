"""Tests for threat_intelligence tools."""

import json
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from purple_mcp.config import ENV_PREFIX, _load_base_settings
from purple_mcp.libs.threat_intelligence import ThreatIntelligenceClient
from purple_mcp.tools import threat_intelligence as ti_tools_module
from purple_mcp.tools.threat_intelligence import (
    threat_intel_by_domain,
    threat_intel_by_hash,
    threat_intel_by_ip,
    threat_intel_by_url,
    threat_intel_get_file_behavior,
    threat_intel_get_file_relationships,
    threat_intel_search,
)


class TestThreatIntelligenceTools:
    """Test threat intelligence tools."""

    @pytest.fixture
    def mock_ti_client(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        """Create a mock TI client with environment-based API key setup."""
        # Set up environment for API key (avoids mocking _get_api_key)
        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "test_console_token")
        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://console.test")
        monkeypatch.setenv(f"{ENV_PREFIX}VT_API_KEY", "test_key")
        _load_base_settings.cache_clear()

        mock_client: AsyncMock = create_autospec(ThreatIntelligenceClient, instance=True)
        mock_client_cls = MagicMock(return_value=mock_client)
        monkeypatch.setattr(ti_tools_module, ThreatIntelligenceClient.__name__, mock_client_cls)
        return mock_client

    # --- threat_intel_by_hash tests ---

    @pytest.mark.asyncio
    async def test_threat_intel_by_hash_success(self, mock_ti_client: AsyncMock) -> None:
        """Test successful hash lookup."""
        test_hash = "44d88612fea8a8f36de82e1278abb02f"
        expected_result = '{"id": "' + test_hash + '", "type": "file"}'
        mock_ti_client.get_hash_threat_intel.return_value = expected_result

        result = await threat_intel_by_hash(test_hash)

        assert result == expected_result
        mock_ti_client.get_hash_threat_intel.assert_called_once_with(test_hash)

    @pytest.mark.asyncio
    async def test_threat_intel_by_hash_not_found(self, mock_ti_client: AsyncMock) -> None:
        """Test hash not found returns structured response."""
        test_hash = "00000000000000000000000000000000"
        not_found_response = json.dumps(
            {
                "found": False,
                "resource": test_hash,
                "resource_type": "file",
                "message": f"File hash '{test_hash}' was not found in VirusTotal's database.",
            }
        )
        mock_ti_client.get_hash_threat_intel.return_value = not_found_response

        result = await threat_intel_by_hash(test_hash)

        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == test_hash

    @pytest.mark.asyncio
    async def test_threat_intel_by_hash_missing_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test missing API key."""
        test_hash = "44d88612fea8a8f36de82e1278abb02f"

        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "test_console_token")
        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://console.test")
        monkeypatch.delenv(f"{ENV_PREFIX}VT_API_KEY", raising=False)
        _load_base_settings.cache_clear()

        with pytest.raises(RuntimeError) as exc_info:
            await threat_intel_by_hash(test_hash)

        error_msg = str(exc_info.value)
        assert "Settings not initialized" in error_msg or "PURPLEMCP_VT_API_KEY" in error_msg

    # --- threat_intel_by_url tests ---

    @pytest.mark.asyncio
    async def test_threat_intel_by_url_success(self, mock_ti_client: AsyncMock) -> None:
        """Test successful URL lookup."""
        test_url = "https://example.com/test"
        expected_result = '{"id": "test_url_id", "type": "url"}'
        mock_ti_client.get_url_threat_intel.return_value = expected_result

        result = await threat_intel_by_url(test_url)

        assert result == expected_result
        mock_ti_client.get_url_threat_intel.assert_called_once_with(test_url)

    @pytest.mark.asyncio
    async def test_threat_intel_by_url_not_found(self, mock_ti_client: AsyncMock) -> None:
        """Test URL not found returns structured response."""
        test_url = "https://nonexistent.example.test"
        not_found_response = json.dumps(
            {
                "found": False,
                "resource": test_url,
                "resource_type": "url",
                "message": f"URL '{test_url}' was not found in VirusTotal's database.",
            }
        )
        mock_ti_client.get_url_threat_intel.return_value = not_found_response

        result = await threat_intel_by_url(test_url)

        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == test_url

    @pytest.mark.asyncio
    async def test_threat_intel_by_url_missing_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test missing API key."""
        test_url = "https://example.com/test"

        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "test_console_token")
        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://console.test")
        monkeypatch.delenv(f"{ENV_PREFIX}VT_API_KEY", raising=False)
        _load_base_settings.cache_clear()

        with pytest.raises(RuntimeError) as exc_info:
            await threat_intel_by_url(test_url)

        error_msg = str(exc_info.value)
        assert "Settings not initialized" in error_msg or "PURPLEMCP_VT_API_KEY" in error_msg

    # --- threat_intel_by_domain tests ---

    @pytest.mark.asyncio
    async def test_threat_intel_by_domain_success(self, mock_ti_client: AsyncMock) -> None:
        """Test domain threat intelligence lookup."""
        test_domain = "example.com"
        expected_result = '{"id": "example.com", "type": "domain"}'
        mock_ti_client.get_domain_threat_intel.return_value = expected_result

        result = await threat_intel_by_domain(test_domain)

        assert result == expected_result
        mock_ti_client.get_domain_threat_intel.assert_called_once_with(test_domain)

    # --- threat_intel_by_ip tests ---

    @pytest.mark.asyncio
    async def test_threat_intel_by_ip_success(self, mock_ti_client: AsyncMock) -> None:
        """Test IP address threat intelligence lookup."""
        test_ip = "8.8.8.8"
        expected_result = '{"id": "8.8.8.8", "type": "ip_address"}'
        mock_ti_client.get_ip_threat_intel.return_value = expected_result

        result = await threat_intel_by_ip(test_ip)

        assert result == expected_result
        mock_ti_client.get_ip_threat_intel.assert_called_once_with(test_ip)

    # --- threat_intel_get_file_relationships tests ---

    @pytest.mark.asyncio
    async def test_threat_intel_get_file_relationships_success(
        self, mock_ti_client: AsyncMock
    ) -> None:
        """Test file relationships retrieval."""
        test_hash = "44d88612fea8a8f36de82e1278abb02f"
        relationship_type = "contacted_domains"
        expected_result = '{"relationships": [], "count": 0}'
        mock_ti_client.get_file_relationships.return_value = expected_result

        result = await threat_intel_get_file_relationships(test_hash, relationship_type)

        assert result == expected_result
        mock_ti_client.get_file_relationships.assert_called_once_with(test_hash, relationship_type)

    # --- threat_intel_search tests ---

    @pytest.mark.asyncio
    async def test_threat_intel_search_success(self, mock_ti_client: AsyncMock) -> None:
        """Test intelligence search."""
        test_query = "type:peexe positives:5+"
        expected_result = '{"results": [], "count": 0, "query": "test"}'
        mock_ti_client.search_intelligence.return_value = expected_result

        result = await threat_intel_search(test_query)

        assert result == expected_result
        mock_ti_client.search_intelligence.assert_called_once_with(test_query)

    # --- threat_intel_get_file_behavior tests ---

    @pytest.mark.asyncio
    async def test_threat_intel_get_file_behavior_success(self, mock_ti_client: AsyncMock) -> None:
        """Test file behavior report retrieval."""
        test_hash = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
        expected_result = '{"id": "test_behavior", "type": "file_behaviour"}'
        mock_ti_client.get_file_behavior.return_value = expected_result

        result = await threat_intel_get_file_behavior(test_hash)

        assert result == expected_result
        mock_ti_client.get_file_behavior.assert_called_once_with(test_hash, None)
