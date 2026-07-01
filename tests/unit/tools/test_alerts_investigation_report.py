"""Tests for the get_alert_investigation_report tool."""

import json
from unittest.mock import AsyncMock, create_autospec

import pytest

from purple_mcp.libs.alerts import AIInvestigation, AlertsClient
from purple_mcp.libs.alerts.exceptions import AlertsGraphQLError
from purple_mcp.tools import alerts


class TestGetAlertInvestigationReport:
    """Test get_alert_investigation_report tool."""

    @pytest.mark.asyncio
    async def test_returns_report_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful report retrieval returns JSON-serialised model."""
        fake_report = AIInvestigation(
            alertId="alert-123",
            result="# Report\nNo threats found.",
            status="COMPLETED",
            verdict="FALSE_POSITIVE",
            timestamp="2024-01-01T00:00:00Z",
            purpleAiStatus="DONE",
        )

        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_investigation_report = AsyncMock(return_value=fake_report)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        result = await alerts.get_alert_investigation_report("alert-123")

        mock_client.get_alert_investigation_report.assert_called_once_with(alert_id="alert-123")
        data = json.loads(result)
        assert data["alertId"] == "alert-123"
        assert data["result"] == "# Report\nNo threats found."
        assert data["status"] == "COMPLETED"
        assert data["verdict"] == "FALSE_POSITIVE"
        assert data["purpleAiStatus"] == "DONE"

    @pytest.mark.asyncio
    async def test_returns_null_json_when_no_report(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that None from the client is serialised as JSON null."""
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_investigation_report = AsyncMock(return_value=None)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        result = await alerts.get_alert_investigation_report("alert-456")

        assert json.loads(result) is None

    @pytest.mark.asyncio
    async def test_excludes_none_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that None-valued optional fields are excluded from the output."""
        fake_report = AIInvestigation(
            alertId="alert-789",
            result="# Report",
            status="COMPLETED",
            verdict="TRUE_POSITIVE",
        )

        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_investigation_report = AsyncMock(return_value=fake_report)
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        result = await alerts.get_alert_investigation_report("alert-789")

        data = json.loads(result)
        assert "timestamp" not in data
        assert "purpleAiStatus" not in data
        assert "investigationStep" not in data

    @pytest.mark.asyncio
    async def test_graphql_error_raises_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a GraphQL error is wrapped in RuntimeError."""
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_investigation_report = AsyncMock(
            side_effect=AlertsGraphQLError("Dummy Error")
        )
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        with pytest.raises(
            RuntimeError, match=r"Failed to retrieve investigation report for alert alert-999"
        ):
            await alerts.get_alert_investigation_report("alert-999")

    @pytest.mark.asyncio
    async def test_value_error_re_raised(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that ValueError is re-raised without wrapping."""
        mock_client = create_autospec(AlertsClient, spec_set=True, instance=True)
        mock_client.get_alert_investigation_report = AsyncMock(
            side_effect=ValueError("invalid alert_id")
        )
        monkeypatch.setattr(alerts, alerts._get_alerts_client.__name__, lambda: mock_client)

        with pytest.raises(ValueError, match=r"invalid alert_id"):
            await alerts.get_alert_investigation_report("")
