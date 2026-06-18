"""Tests for CVE client."""

import functools
import json
from collections.abc import Callable
from http import HTTPStatus

import httpx
import pytest

from purple_mcp.libs.cve import CVEClient, CVEClientError, CVEConfig


class TestCVEClient:
    """Test CVE client class."""

    @pytest.fixture
    def config(self) -> CVEConfig:
        """Create a test CVE config."""
        return CVEConfig(base_url="https://test.example.com", timeout=10.0)

    @pytest.fixture
    def client(self, config: CVEConfig) -> CVEClient:
        """Create a test CVE client."""
        return CVEClient(config)

    def _setup_mock_transport(
        self,
        monkeypatch: pytest.MonkeyPatch,
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> None:
        """Set up httpx mock transport with the given request handler."""
        mock_transport = httpx.MockTransport(handler)
        mock_client = functools.partial(httpx.AsyncClient, transport=mock_transport)
        monkeypatch.setattr(httpx, httpx.AsyncClient.__name__, mock_client)

    @pytest.mark.asyncio
    async def test_get_cve_by_id_success(
        self, client: CVEClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successful CVE lookup by ID."""
        mock_response = {
            "id": "CVE-2024-47176",
            "summary": "Test vulnerability",
            "cvss": 7.5,
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://test.example.com/cve/CVE-2024-47176"
            return httpx.Response(HTTPStatus.OK, json=mock_response)

        self._setup_mock_transport(monkeypatch, handler)

        result = await client.get_cve_by_id("CVE-2024-47176")

        assert json.loads(result) == mock_response

    @pytest.mark.asyncio
    async def test_get_cve_by_id_not_found(
        self, client: CVEClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CVE not found returns structured response."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://test.example.com/cve/CVE-9999-99999"
            return httpx.Response(HTTPStatus.NOT_FOUND)

        self._setup_mock_transport(monkeypatch, handler)

        result = await client.get_cve_by_id("CVE-9999-99999")

        # Verify structured not-found response
        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == "CVE-9999-99999"
        assert response["resource_type"] == "cve"
        assert "CVE-9999-99999" in response["message"]
        assert "not found" in response["message"].lower()

    @pytest.mark.asyncio
    async def test_search_by_vendor_product_success(
        self, client: CVEClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successful vendor/product search."""
        mock_response = [
            {"id": "CVE-2024-1", "summary": "Vuln 1"},
            {"id": "CVE-2024-2", "summary": "Vuln 2"},
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://test.example.com/search/microsoft/windows"
            return httpx.Response(HTTPStatus.OK, json=mock_response)

        self._setup_mock_transport(monkeypatch, handler)

        result = await client.search_by_vendor_product("microsoft", "windows")

        assert json.loads(result) == mock_response

    @pytest.mark.asyncio
    async def test_search_by_vendor_only_success(
        self, client: CVEClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successful vendor-only search (browse products)."""
        mock_response = ["windows", "office", "azure"]

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://test.example.com/browse/microsoft"
            return httpx.Response(HTTPStatus.OK, json=mock_response)

        self._setup_mock_transport(monkeypatch, handler)

        result = await client.search_by_vendor_product("microsoft")

        assert json.loads(result) == mock_response

    @pytest.mark.asyncio
    async def test_search_by_vendor_product_not_found(
        self, client: CVEClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test vendor/product not found returns structured response."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://test.example.com/search/unknown/product"
            return httpx.Response(HTTPStatus.NOT_FOUND)

        self._setup_mock_transport(monkeypatch, handler)

        result = await client.search_by_vendor_product("unknown", "product")

        # Verify structured not-found response
        response = json.loads(result)
        assert response["found"] is False
        assert response["resource"] == "unknown/product"
        assert response["resource_type"] == "vendor_product"
        assert "unknown" in response["message"]
        assert "product" in response["message"]
        assert "no results found" in response["message"].lower()

    @pytest.mark.asyncio
    async def test_get_database_info_success(
        self, client: CVEClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test getting database info."""
        mock_response = {
            "last_update": "2024-01-15T10:30:00Z",
            "count": 250000,
            "version": "1.0",
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == "https://test.example.com/dbInfo"
            return httpx.Response(HTTPStatus.OK, json=mock_response)

        self._setup_mock_transport(monkeypatch, handler)

        result = await client.get_database_info()

        assert json.loads(result) == mock_response

    @pytest.mark.parametrize(
        ("method_name", "method_args"),
        [
            ("get_cve_by_id", ("CVE-2024-1234",)),
            ("search_by_vendor_product", ("microsoft", "windows")),
            ("search_by_vendor_product", ("microsoft", None)),
            ("get_database_info", ()),
        ],
    )
    @pytest.mark.asyncio
    async def test_request_errors_raise_cve_client_error(
        self,
        client: CVEClient,
        monkeypatch: pytest.MonkeyPatch,
        method_name: str,
        method_args: tuple[str | None, ...],
    ) -> None:
        """Request-level errors should be wrapped in CVEClientError."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Simulated failure")

        self._setup_mock_transport(monkeypatch, handler)

        with pytest.raises(CVEClientError, match="Error communicating with CVE API"):
            method = getattr(client, method_name)
            await method(*method_args)

    @pytest.mark.parametrize(
        ("method_name", "method_args"),
        [
            ("get_cve_by_id", ("CVE-2024-1234",)),
            ("search_by_vendor_product", ("microsoft", "windows")),
            ("search_by_vendor_product", ("microsoft", None)),
            ("get_database_info", ()),
        ],
    )
    @pytest.mark.asyncio
    async def test_http_status_errors_raise_cve_client_error(
        self,
        client: CVEClient,
        monkeypatch: pytest.MonkeyPatch,
        method_name: str,
        method_args: tuple[str | None, ...],
    ) -> None:
        """Non-404 HTTP errors should raise CVEClientError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                HTTPStatus.INTERNAL_SERVER_ERROR, text=HTTPStatus.INTERNAL_SERVER_ERROR.phrase
            )

        self._setup_mock_transport(monkeypatch, handler)

        with pytest.raises(CVEClientError, match="HTTP error from CVE API"):
            method = getattr(client, method_name)
            await method(*method_args)
