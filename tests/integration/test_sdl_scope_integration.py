"""Test that SDL queries have correct scope behaviour."""

import asyncio
import logging
import os
from datetime import datetime, timedelta

import pytest

from purple_mcp.config import (
    SDL_CONSOLE_ACCOUNT_IDS_ENV,
    SDL_INT_TEST_AGENT_EVENT_TIMESTAMP_ENV,
    SDL_INT_TEST_AGENT_UUID_ENV,
    SDL_INT_TEST_SECOND_ACCOUNT_ID_ENV,
)
from purple_mcp.tools.sdl import powerquery
from tests.integration.conftest import load_test_env

logger = logging.getLogger(__name__)


REQUIRED_ENV_VARS = (
    SDL_CONSOLE_ACCOUNT_IDS_ENV,
    SDL_INT_TEST_SECOND_ACCOUNT_ID_ENV,
    SDL_INT_TEST_AGENT_UUID_ENV,
    SDL_INT_TEST_AGENT_EVENT_TIMESTAMP_ENV,
)


def _check_for_undefined_env_vars() -> list[str]:
    load_test_env()
    undefined_env_vars = [env_var for env_var in REQUIRED_ENV_VARS if env_var not in os.environ]
    return undefined_env_vars


undefined_env_vars = _check_for_undefined_env_vars()

TEST_AGENT_UUID = os.environ.get(SDL_INT_TEST_AGENT_UUID_ENV)
PRIMARY_ACCOUNT_ID = os.environ.get(SDL_CONSOLE_ACCOUNT_IDS_ENV)
SECONDARY_ACCOUNT_ID = os.environ.get(SDL_INT_TEST_SECOND_ACCOUNT_ID_ENV)
TIME_WINDOW_CENTRE_TIMESTAMP = os.environ.get(SDL_INT_TEST_AGENT_EVENT_TIMESTAMP_ENV)

DEFAULT_QUERY = f'''\
| filter( agent.uuid == "{TEST_AGENT_UUID}")
| columns event.time, event.id, event.type, agent.uuid, src.process.storyline.id, src.process.user, src.process.uid
| sort event.time
| limit 3'''


@pytest.fixture()
def time_window_containing_agent_events() -> tuple[str, str]:
    """Create start & end timestamps using supplied timestamp as a midpoint."""
    # Use narrow 10-minute window
    time_window_half_width = timedelta(minutes=5)
    if TIME_WINDOW_CENTRE_TIMESTAMP is None:
        raise RuntimeError(
            f"Fixture time_window_containing_agent_events called despite undefined env-var {SDL_INT_TEST_AGENT_EVENT_TIMESTAMP_ENV}"
        )
    time_window_centre = datetime.fromisoformat(TIME_WINDOW_CENTRE_TIMESTAMP)
    time_stamp_start = (
        (time_window_centre - time_window_half_width).isoformat().replace("+00:00", "Z")
    )
    time_stamp_end = (
        (time_window_centre + time_window_half_width).isoformat().replace("+00:00", "Z")
    )
    return time_stamp_start, time_stamp_end


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(
    any(undefined_env_vars),
    reason=f"Skipping due to undefined required env vars: {undefined_env_vars}",
)
@pytest.mark.parametrize("account_id", [None, PRIMARY_ACCOUNT_ID])
async def test_scope_access_for_s1_main_account(
    account_id: str | None,
    integration_settings: None,
    integration_timeout: int,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    time_window_containing_agent_events: tuple[str, str],
) -> None:
    """Test PowerQuery tool function directly, exercising Tenant / Account scoped queries.

    This test should pass whether using a service-user token or console-API token.
    """
    caplog.set_level(logging.INFO)

    start_datetime, end_datetime = time_window_containing_agent_events
    if account_id is None:
        monkeypatch.delenv(SDL_CONSOLE_ACCOUNT_IDS_ENV, raising=False)
    else:
        monkeypatch.setenv(SDL_CONSOLE_ACCOUNT_IDS_ENV, str(account_id))

    result = await asyncio.wait_for(
        powerquery(
            query=DEFAULT_QUERY,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        ),
        timeout=integration_timeout * 2,
    )

    assert isinstance(result, str)

    # Should contain either results or error message
    assert len(result) > 0, "Should return some result"
    assert isinstance(result, str), "Result should be a string"

    logger.debug(
        "Direct PowerQuery function success: result_length=%d, preview=%s...",
        len(result),
        result[:200],
    )

    expected_log_fragment = (
        "SDL query with account scope"
        if account_id
        else "SDL query with global scope (all accessible accounts)"
    )
    assert expected_log_fragment in caplog.text


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(
    any(undefined_env_vars),
    reason=f"Skipping due to undefined required env vars: {undefined_env_vars}",
)
async def test_scope_access_for_out_of_scope_account(
    integration_settings: None,
    integration_timeout: int,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    time_window_containing_agent_events: tuple[str, str],
) -> None:
    """Test PowerQuery tool function directly, exercising  Account scoped queries.

    We expect no results here as we're explicitly narrowing scope to an account where this
    Agent UUID is not present.

    Again this should work for either a console-api or service-user token.
    """
    caplog.set_level(logging.INFO)
    start_datetime, end_datetime = time_window_containing_agent_events
    monkeypatch.setenv(SDL_CONSOLE_ACCOUNT_IDS_ENV, str(SECONDARY_ACCOUNT_ID))

    result = await asyncio.wait_for(
        powerquery(
            query=DEFAULT_QUERY,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        ),
        timeout=integration_timeout * 2,
    )

    assert isinstance(result, str)
    assert not result

    expected_log_fragment = "SDL query with account scope"
    assert expected_log_fragment in caplog.text
