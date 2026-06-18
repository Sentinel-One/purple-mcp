"""Tests for threat_intelligence client."""

import json
from unittest.mock import MagicMock, create_autospec

import aiohttp
import pytest
import vt

from purple_mcp.libs.threat_intelligence import (
    ThreatIntelligenceClient,
    ThreatIntelligenceClientError,
    ThreatIntelligenceConfig,
)
from purple_mcp.libs.threat_intelligence.client import VTErrors


class TestThreatIntelligenceClient:
    """Test ThreatIntelligenceClient."""

    @pytest.fixture
    def config(self) -> ThreatIntelligenceConfig:
        """Create a test config."""
        return ThreatIntelligenceConfig(
            api_key="test_api_key",
            timeout=30.0,
        )

    @pytest.fixture
    def client(self, config: ThreatIntelligenceConfig) -> ThreatIntelligenceClient:
        """Create a test client."""
        return ThreatIntelligenceClient(config)

    @pytest.fixture
    def mocked_vt_client(self, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        """Create a mocked vt Client."""
        mock_vt_client: MagicMock = create_autospec(vt.Client, instance=True)
        mock_vt_client.__aenter__.return_value = mock_vt_client
        mock_vt_client.__aexit__.return_value = None
        monkeypatch.setattr(vt, vt.Client.__name__, lambda *args, **kwargs: mock_vt_client)
        return mock_vt_client

    @pytest.mark.asyncio
    async def test_get_hash_threat_intel_success(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test successful hash lookup."""
        test_hash = "44d88612fea8a8f36de82e1278abb02f"
        mocked_vt_client.get_json_async.return_value = {
            "data": {
                "id": test_hash,
                "type": "file",
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 45,
                        "suspicious": 2,
                        "undetected": 23,
                    }
                },
            }
        }

        result = await client.get_hash_threat_intel(test_hash)

        assert test_hash in result
        assert "malicious" in result
        mocked_vt_client.get_json_async.assert_called_once_with(f"/files/{test_hash}")

    @pytest.mark.asyncio
    async def test_get_hash_threat_intel_not_found(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test hash not found returns structured response."""
        test_hash = "00000000000000000000000000000000"

        mocked_vt_client.get_json_async.side_effect = vt.error.APIError(
            VTErrors.NotFoundError, "Not found"
        )

        result = await client.get_hash_threat_intel(test_hash)

        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == test_hash
        assert response["resource_type"] == "file"
        assert "not found" in response["message"].lower()
        assert test_hash in response["message"]

    @pytest.mark.asyncio
    async def test_get_url_threat_intel_success(
        self,
        client: ThreatIntelligenceClient,
        mocked_vt_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test successful URL lookup."""
        test_url = "https://example.com/test"
        mocked_vt_client.get_json_async.return_value = {
            "data": {
                "id": "test_url_id",
                "type": "url",
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 5,
                        "suspicious": 1,
                        "undetected": 84,
                    }
                },
            }
        }
        mock_url_id = MagicMock(return_value="test_url_id")
        monkeypatch.setattr(vt, vt.url_id.__name__, mock_url_id)

        result = await client.get_url_threat_intel(test_url)

        assert "test_url_id" in result
        assert "malicious" in result
        mock_url_id.assert_called_once_with(test_url)

    @pytest.mark.asyncio
    async def test_get_url_threat_intel_not_found(
        self,
        client: ThreatIntelligenceClient,
        mocked_vt_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test URL not found returns structured response."""
        test_url = "https://nonexistent.example.test"
        mocked_vt_client.get_json_async.side_effect = vt.error.APIError(
            VTErrors.NotFoundError, "Not found"
        )
        monkeypatch.setattr(vt, vt.url_id.__name__, MagicMock(return_value="test_url_id"))

        result = await client.get_url_threat_intel(test_url)

        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == test_url
        assert response["resource_type"] == "url"
        assert "not found" in response["message"].lower()
        assert test_url in response["message"]

    @pytest.mark.asyncio
    async def test_get_domain_threat_intel_success(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test successful domain lookup."""
        test_domain = "example.com"
        mocked_vt_client.get_json_async.return_value = {
            "data": {
                "id": test_domain,
                "type": "domain",
                "attributes": {"reputation": 90, "categories": {"security": "safe"}},
            }
        }

        result = await client.get_domain_threat_intel(test_domain)

        assert test_domain in result
        assert "reputation" in result
        mocked_vt_client.get_json_async.assert_called_once_with(f"/domains/{test_domain}")

    @pytest.mark.asyncio
    async def test_get_ip_threat_intel_success(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test successful IP lookup."""
        test_ip = "8.8.8.8"
        mocked_vt_client.get_json_async.return_value = {
            "data": {
                "id": test_ip,
                "type": "ip_address",
                "attributes": {"reputation": 100, "country": "US"},
            }
        }

        result = await client.get_ip_threat_intel(test_ip)

        assert test_ip in result
        assert "reputation" in result
        mocked_vt_client.get_json_async.assert_called_once_with(f"/ip_addresses/{test_ip}")

    @pytest.mark.asyncio
    async def test_get_file_relationships_success(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test successful file relationships retrieval uses config limit."""
        test_hash = "44d88612fea8a8f36de82e1278abb02f"
        relationship_type = "contacted_domains"

        domain1 = "example.com"
        domain2 = "test.com"
        mock_rel_obj1 = MagicMock()
        mock_rel_obj1.to_dict.return_value = {"id": domain1, "type": "domain"}
        mock_rel_obj2 = MagicMock()
        mock_rel_obj2.to_dict.return_value = {"id": domain2, "type": "domain"}
        mocked_vt_client.iterator.return_value.__aiter__.return_value = iter(
            [mock_rel_obj1, mock_rel_obj2]
        )

        result = await client.get_file_relationships(test_hash, relationship_type)

        assert "relationships" in result
        assert "count" in result
        assert domain1 in result
        assert domain2 in result
        mocked_vt_client.iterator.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_intelligence_success(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test successful intelligence search uses config limit."""
        test_query = "type:peexe positives:5+"

        mock_result1 = MagicMock()
        mock_result1.to_dict.return_value = {
            "id": "hash1",
            "type": "file",
            "attributes": {"positives": 10},
        }
        mock_result2 = MagicMock()
        mock_result2.to_dict.return_value = {
            "id": "hash2",
            "type": "file",
            "attributes": {"positives": 15},
        }
        mocked_vt_client.iterator.return_value.__aiter__.return_value = iter(
            [mock_result1, mock_result2]
        )

        result = await client.search_intelligence(test_query)

        assert "results" in result
        assert "count" in result
        assert "query" in result
        assert test_query in result
        mocked_vt_client.iterator.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_file_behavior_success(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test successful file behavior retrieval uses config limit."""
        test_hash = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"

        mock_behavior = MagicMock()
        mock_behavior.to_dict.return_value = {
            "id": f"{test_hash}_VirusTotal_Jujubox",
            "type": "file_behaviour",
            "attributes": {"processes": [], "network": {}},
        }
        mocked_vt_client.iterator.return_value.__aiter__.return_value = iter([mock_behavior])

        result = await client.get_file_behavior(test_hash)

        assert "file_behaviour" in result
        assert "processes" in result
        mocked_vt_client.iterator.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_file_behavior_not_found(
        self, client: ThreatIntelligenceClient, mocked_vt_client: MagicMock
    ) -> None:
        """Test file behavior not found returns structured response."""
        test_hash = "00000000000000000000000000000000"
        mocked_vt_client.iterator.return_value.__aiter__.return_value = iter([])

        result = await client.get_file_behavior(test_hash)

        # Verify structured not-found response
        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == test_hash
        assert response["resource_type"] == "file"
        assert "No behavioral analysis reports found" in response["message"]

    @pytest.mark.parametrize(
        ("method_name", "method_args"),
        [
            ("get_hash_threat_intel", ("abc123hash",)),
            ("get_url_threat_intel", ("https://example.test",)),
            ("get_domain_threat_intel", ("example.test",)),
            ("get_ip_threat_intel", ("192.0.2.1",)),
            ("get_file_relationships", ("abc123hash", "contacted_domains")),
            ("search_intelligence", ("type:peexe",)),
            ("get_file_behavior", ("abc123hash",)),
        ],
    )
    @pytest.mark.asyncio
    async def test_vt_api_errors_raise_threat_intel_client_error(
        self,
        client: ThreatIntelligenceClient,
        mocked_vt_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        method_name: str,
        method_args: tuple[str, ...],
    ) -> None:
        """VT API errors (non-404) should raise ThreatIntelligenceClientError."""
        monkeypatch.setattr(vt, vt.url_id.__name__, MagicMock(return_value="test_url_id"))

        api_error = vt.error.APIError(VTErrors.QuotaExceededError, "Test error")
        mocked_vt_client.get_json_async.side_effect = api_error
        mocked_vt_client.iterator.return_value.__aiter__.side_effect = api_error

        with pytest.raises(ThreatIntelligenceClientError):
            method = getattr(client, method_name)
            await method(*method_args)

    @pytest.mark.parametrize(
        ("method_name", "method_args"),
        [
            ("get_hash_threat_intel", ("abc123hash",)),
            ("get_url_threat_intel", ("https://example.test",)),
            ("get_domain_threat_intel", ("example.test",)),
            ("get_ip_threat_intel", ("192.0.2.1",)),
            ("get_file_relationships", ("abc123hash", "contacted_domains")),
            ("search_intelligence", ("type:peexe",)),
            ("get_file_behavior", ("abc123hash",)),
        ],
    )
    @pytest.mark.asyncio
    async def test_network_errors_raise_threat_intel_client_error(
        self,
        client: ThreatIntelligenceClient,
        mocked_vt_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        method_name: str,
        method_args: tuple[str, ...],
    ) -> None:
        """Network errors should raise ThreatIntelligenceClientError."""
        monkeypatch.setattr(vt, vt.url_id.__name__, MagicMock(return_value="test_url_id"))

        exc = aiohttp.ClientError("Simulated failure")
        mocked_vt_client.get_json_async.side_effect = exc
        mocked_vt_client.iterator.return_value.__aiter__.side_effect = exc

        with pytest.raises(ThreatIntelligenceClientError, match="Network error"):
            method = getattr(client, method_name)
            await method(*method_args)
