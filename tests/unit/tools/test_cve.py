"""Tests for CVE tools."""

import json
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from purple_mcp.libs.cve import CVEClient
from purple_mcp.tools import cve as cve_tools_module
from purple_mcp.tools.cve import cve_database_status, cve_search_by_id, cve_search_by_vendor


class TestCVETools:
    """Test CVE tools."""

    @pytest.fixture
    def mock_cve_client(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        """Create a mock CVE client that can be configured per test."""
        mock_client: AsyncMock = create_autospec(CVEClient, instance=True)
        mock_client_cls = MagicMock(return_value=mock_client)

        monkeypatch.setattr(cve_tools_module, CVEClient.__name__, mock_client_cls)
        return mock_client

    @pytest.mark.asyncio
    async def test_cve_search_by_id_success(self, mock_cve_client: AsyncMock) -> None:
        """Test successful CVE search by ID."""
        mock_cve_data = {
            "id": "CVE-2024-47176",
            "summary": "Test vulnerability description",
            "cvss": 7.5,
            "cvss3": {"score": 9.1},
        }
        mock_cve_client.get_cve_by_id.return_value = json.dumps(mock_cve_data)

        result = await cve_search_by_id("CVE-2024-47176")

        assert json.loads(result) == mock_cve_data
        mock_cve_client.get_cve_by_id.assert_called_once_with("CVE-2024-47176")

    @pytest.mark.asyncio
    async def test_cve_search_by_id_not_found(self, mock_cve_client: AsyncMock) -> None:
        """Test CVE not found returns structured response."""
        cve_id = "CVE-9999-99999"
        not_found_response = json.dumps(
            {
                "found": False,
                "resource": cve_id,
                "resource_type": "cve",
                "message": f"CVE {cve_id} not found in database",
            },
        )
        mock_cve_client.get_cve_by_id.return_value = not_found_response

        result = await cve_search_by_id(cve_id)

        # Verify structured not-found response
        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == cve_id
        assert response["resource_type"] == "cve"

    @pytest.mark.asyncio
    async def test_cve_search_by_vendor_with_product(self, mock_cve_client: AsyncMock) -> None:
        """Test CVE search by vendor and product."""
        mock_cves = [
            {"id": "CVE-2024-1", "summary": "Vulnerability 1"},
            {"id": "CVE-2024-2", "summary": "Vulnerability 2"},
        ]
        mock_cve_client.search_by_vendor_product.return_value = json.dumps(mock_cves)

        result = await cve_search_by_vendor("microsoft", "windows")

        assert json.loads(result) == mock_cves
        mock_cve_client.search_by_vendor_product.assert_called_once_with("microsoft", "windows")

    @pytest.mark.asyncio
    async def test_cve_search_by_vendor_without_product(self, mock_cve_client: AsyncMock) -> None:
        """Test CVE search by vendor only (browse products)."""
        mock_products = ["windows", "office", "azure"]
        mock_cve_client.search_by_vendor_product.return_value = json.dumps(mock_products)

        result = await cve_search_by_vendor("microsoft")

        assert json.loads(result) == mock_products
        mock_cve_client.search_by_vendor_product.assert_called_once_with("microsoft", None)

    @pytest.mark.asyncio
    async def test_cve_search_by_vendor_not_found(self, mock_cve_client: AsyncMock) -> None:
        """Test vendor/product not found returns structured response."""
        vendor = "unknown"
        product = "product"
        not_found_response = json.dumps(
            {
                "found": False,
                "resource": f"{vendor}/{product}",
                "resource_type": "vendor_product",
                "message": f"No results found for vendor '{vendor}' and product '{product}'",
            },
        )
        mock_cve_client.search_by_vendor_product.return_value = not_found_response

        result = await cve_search_by_vendor(vendor, product)

        # Verify structured not-found response
        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == f"{vendor}/{product}"
        assert response["resource_type"] == "vendor_product"

    @pytest.mark.asyncio
    async def test_cve_database_status_success(self, mock_cve_client: AsyncMock) -> None:
        """Test getting database status."""
        mock_status = {
            "last_update": "2024-01-15T10:30:00Z",
            "count": 250000,
            "version": "1.0",
        }
        mock_cve_client.get_database_info.return_value = json.dumps(mock_status)

        result = await cve_database_status()

        assert json.loads(result) == mock_status
        mock_cve_client.get_database_info.assert_called_once()
