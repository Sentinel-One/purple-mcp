"""Tests for alerts tools."""

import json
from unittest.mock import AsyncMock, create_autospec

import pytest

from purple_mcp.libs.alerts import (
    Alert,
    AlertConnection,
    AlertHistoryConnection,
    AlertNoteConnection,
    AlertsClient,
    AlertsClientError,
    AlertsGraphQLError,
    Severity,
    Status,
)
from purple_mcp.tools import alerts
from purple_mcp.type_defs import JsonDict
from tests.unit.libs.alerts.helpers import MockAlertsClientBuilder


@pytest.fixture()
def fake_alert() -> Alert:
    """Create a fake alert for testing."""
    alert_id = "alert-123"
    name = "Test Alert"
    severity = "HIGH"
    status = "NEW"
    timestamp = "2024-01-01T00:00:00Z"

    return Alert(
        id=alert_id,
        name=name,
        severity=Severity(severity),
        status=Status(status),
        detectedAt=timestamp,
    )


class TestGetAlert:
    """Test get_alert tool."""

    @pytest.mark.asyncio
    async def test_get_alert_success(
        self, fake_alert: Alert, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successful alert retrieval."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert = AsyncMock(return_value=fake_alert)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        result = await alerts.get_alert(fake_alert.id)

        # assert
        # check method
        mock_client.get_alert.assert_called_with(alert_id=fake_alert.id)
        # check result
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, dict)
        fake_alert_dict = fake_alert.model_dump(mode="json")
        for k, v in data.items():
            assert v == fake_alert_dict[k]

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test alert not found raises an error."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert = AsyncMock(side_effect=AlertsGraphQLError("Dummy Error"))
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        with pytest.raises(RuntimeError, match=r"Failed to retrieve alert nonexistent-alert"):
            await alerts.get_alert("nonexistent-alert")

    @pytest.mark.asyncio
    async def test_get_alert_client_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test client error handling."""
        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert = AsyncMock(side_effect=AlertsClientError("Network error"))
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)
        with pytest.raises(RuntimeError, match=r"Failed to retrieve alert"):
            await alerts.get_alert("dummy-alert-id")


class TestListAlerts:
    """Test list_alerts tool."""

    @pytest.mark.asyncio
    async def test_list_alerts_success_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful alerts listing."""
        empty_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)

        # arrange
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.list_alerts = AsyncMock(return_value=empty_connection)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        result = await alerts.list_alerts()

        # assert
        data: JsonDict = json.loads(result)
        assert "edges" in data
        assert "pageInfo" in data
        assert data["edges"] == []

    @pytest.mark.parametrize(
        "first_value,expected_error",
        [
            (0, "first must be between 1 and 100"),
            (101, "first must be between 1 and 100"),
            (-1, "first must be between 1 and 100"),
        ],
    )
    @pytest.mark.asyncio
    async def test_list_alerts_invalid_first_parameter(
        self, first_value: int, expected_error: str
    ) -> None:
        """Test validation of first parameter."""
        with pytest.raises(ValueError, match=expected_error):
            await alerts.list_alerts(first=first_value)

    @pytest.mark.asyncio
    async def test_list_alerts_invalid_view_type(self) -> None:
        """Test validation of view_type parameter."""
        with pytest.raises(ValueError, match="view_type must be one of:"):
            await alerts.list_alerts(view_type="INVALID_TYPE")


class TestSearchAlerts:
    """Test search_alerts function."""

    @pytest.mark.asyncio
    async def test_search_alerts_without_filters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search without filters."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.search_alerts = AsyncMock(return_value=mock_connection)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        result = await alerts.search_alerts()

        # assert
        data: JsonDict = json.loads(result)
        assert "edges" in data
        assert "pageInfo" in data
        assert data["edges"] == []

    @pytest.mark.asyncio
    async def test_search_alerts_with_filters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search without filters."""
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertConnection)
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.search_alerts = AsyncMock(return_value=mock_connection)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)
        filters_str = json.dumps(
            [
                {
                    "fieldId": "severity",
                    "filterType": "string_in",
                    "values": ["HIGH", "CRITICAL"],
                },
                {"fieldId": "priority", "filterType": "int_in", "values": [1, 2, 3]},
            ]
        )

        result = await alerts.search_alerts(filters=filters_str)

        # assert
        data: JsonDict = json.loads(result)
        assert "edges" in data
        assert "pageInfo" in data
        assert data["edges"] == []

    @pytest.mark.parametrize(
        "invalid_filters,expected_error",
        [
            (
                [{"field": "severity"}],
                "Each filter must have 'fieldId' and 'filterType' keys",
            ),
            (
                [{"fieldId": "severity", "filterType": "INVALID_TYPE", "value": "HIGH"}],
                "Invalid filter format",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_alerts_invalid_filters(
        self, invalid_filters: list[dict[str, str]], expected_error: str
    ) -> None:
        """Test validation of filter format."""
        filters_str = json.dumps(invalid_filters)
        with pytest.raises(ValueError, match=expected_error):
            await alerts.search_alerts(filters=filters_str)


class TestGetAlertNotes:
    """Test get_alert_notes tool."""

    @pytest.mark.asyncio
    async def test_get_alert_notes_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful notes retrieval."""
        # arrange
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertNoteConnection)
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_notes = AsyncMock(return_value=mock_connection)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        result = await alerts.get_alert_notes("alert-123")

        # assert
        mock_client.get_alert_notes.assert_called_with(alert_id="alert-123")
        data: JsonDict = json.loads(result)
        assert "edges" in data
        assert "pageInfo" in data
        assert data["edges"] == []


class TestCursorValidation:
    """Test cursor validation across all functions."""

    @pytest.mark.asyncio
    async def test_list_alerts_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected."""
        with pytest.raises(ValueError, match="Cursor cannot be empty"):
            await alerts.list_alerts(first=10, after="")

    @pytest.mark.asyncio
    async def test_list_alerts_invalid_cursor_whitespace_only(self) -> None:
        """Test that whitespace-only cursors are rejected."""
        with pytest.raises(ValueError, match="Cursor cannot be empty"):
            await alerts.list_alerts(first=10, after="   \t\n  ")

    @pytest.mark.asyncio
    async def test_get_alert_history_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected for alert history."""
        with pytest.raises(ValueError, match="Cursor cannot be empty"):
            await alerts.get_alert_history(alert_id="test-123", first=10, after="")

    @pytest.mark.asyncio
    async def test_get_alert_history_empty_alert_id(self) -> None:
        """Test that empty alert IDs are rejected."""
        with pytest.raises(ValueError, match="Alert ID cannot be empty"):
            await alerts.get_alert_history(alert_id="", first=10)

    @pytest.mark.asyncio
    async def test_get_alert_history_whitespace_alert_id(self) -> None:
        """Test that whitespace-only alert IDs are rejected."""
        with pytest.raises(ValueError, match="Alert ID cannot be empty"):
            await alerts.get_alert_history(alert_id="   \t\n  ", first=10)

    @pytest.mark.asyncio
    async def test_search_alerts_invalid_cursor_empty_string(self) -> None:
        """Test that empty string cursors are rejected in search_alerts."""
        with pytest.raises(ValueError, match="Cursor cannot be empty"):
            await alerts.search_alerts(first=10, after="")

    @pytest.mark.asyncio
    async def test_search_alerts_invalid_cursor_whitespace_only(self) -> None:
        """Test that whitespace-only cursors are rejected in search_alerts."""
        with pytest.raises(ValueError, match="Cursor cannot be empty"):
            await alerts.search_alerts(first=10, after="   \t\n  ")

    @pytest.mark.asyncio
    async def test_get_alert_history_alert_id_trimmed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that alert IDs are properly trimmed."""
        # arrange
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertHistoryConnection)
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_history = AsyncMock(return_value=mock_connection)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        await alerts.get_alert_history(alert_id="  test-123  ", first=10)

        # assert - Verify the alert_id was trimmed
        mock_client.get_alert_history.assert_called_once()
        call_args = mock_client.get_alert_history.call_args
        assert call_args[1]["alert_id"] == "test-123"


class TestGetAlertHistory:
    """Test get_alert_history function."""

    @pytest.mark.asyncio
    async def test_get_alert_history_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful history retrieval."""
        # arrange
        mock_connection = MockAlertsClientBuilder.create_empty_connection(AlertHistoryConnection)
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_history = AsyncMock(return_value=mock_connection)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        # act
        result = await alerts.get_alert_history(alert_id="alert-123")

        # assert
        mock_client.get_alert_history.assert_called_with(
            alert_id="alert-123", first=10, after=None
        )
        data: JsonDict = json.loads(result)
        assert "edges" in data
        assert "pageInfo" in data
        assert data["edges"] == []
