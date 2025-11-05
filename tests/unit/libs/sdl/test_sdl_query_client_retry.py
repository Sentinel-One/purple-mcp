"""Unit tests for SDLQueryClient retry policy configuration.

These tests verify that the retry policy correctly interprets http_max_retries
as the number of retries (not attempts), and handles edge cases like zero retries.
"""

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from purple_mcp.libs.sdl import SDLQueryClient, create_sdl_settings


@pytest.fixture
def base_url() -> str:
    """Base URL for SDL API."""
    return "https://test.example.test/sdl"


@pytest.fixture
def auth_token() -> str:
    """Test auth token."""
    return "Bearer test-token"


def create_client_with_retries(
    base_url: str,
    http_max_retries: int,
) -> SDLQueryClient:
    """Create an SDL client with a specific retry count.

    Args:
        base_url: Base URL for SDL API
        http_max_retries: Number of retries to configure

    Returns:
        SDLQueryClient instance
    """
    settings = create_sdl_settings(
        base_url=base_url,
        auth_token="Bearer test-token",
        http_timeout=10,
        max_timeout_seconds=60,
        http_max_retries=http_max_retries,
    )
    return SDLQueryClient(base_url, settings)


@pytest.fixture
async def client_zero_retries(base_url: str) -> AsyncGenerator[SDLQueryClient, None]:
    """Yield an SDLQueryClient with zero retries that closes after the test."""
    client = create_client_with_retries(base_url, http_max_retries=0)
    try:
        yield client
    finally:
        if not client.is_closed():
            await client.close()


@pytest.fixture
async def client_one_retry(base_url: str) -> AsyncGenerator[SDLQueryClient, None]:
    """Yield an SDLQueryClient with one retry that closes after the test."""
    client = create_client_with_retries(base_url, http_max_retries=1)
    try:
        yield client
    finally:
        if not client.is_closed():
            await client.close()


@pytest.fixture
async def client_three_retries(base_url: str) -> AsyncGenerator[SDLQueryClient, None]:
    """Yield an SDLQueryClient with three retries that closes after the test."""
    client = create_client_with_retries(base_url, http_max_retries=3)
    try:
        yield client
    finally:
        if not client.is_closed():
            await client.close()


class TestSDLQueryClientRetryPolicy:
    """Test suite for retry policy configuration."""

    def test_retry_policy_zero_retries_means_one_attempt(
        self, client_zero_retries: SDLQueryClient
    ) -> None:
        """Test that http_max_retries=0 results in exactly 1 attempt (no retries).

        This is the critical edge case: with 0 retries, the request should be
        attempted once but not retried on failure.
        """
        # The retry policy should be configured to stop after 1 attempt (0 retries + 1)
        assert client_zero_retries.http_max_retries == 0

        # Verify the retry policy is configured correctly
        # stop_after_attempt(1) means: 1 attempt, 0 retries
        retry_policy = client_zero_retries.retry_policy
        stop_policy = retry_policy.stop
        assert hasattr(stop_policy, "max_attempt_number")
        assert stop_policy.max_attempt_number == 1

    def test_retry_policy_one_retry_means_two_attempts(
        self, client_one_retry: SDLQueryClient
    ) -> None:
        """Test that http_max_retries=1 results in exactly 2 attempts (1 initial + 1 retry).

        The setting name is http_max_retries, so 1 retry = 2 total attempts.
        """
        assert client_one_retry.http_max_retries == 1

        # Verify the retry policy is configured correctly
        # stop_after_attempt(2) means: 1 initial attempt + 1 retry = 2 attempts
        retry_policy = client_one_retry.retry_policy
        stop_policy = retry_policy.stop
        assert hasattr(stop_policy, "max_attempt_number")
        assert stop_policy.max_attempt_number == 2

    def test_retry_policy_three_retries_means_four_attempts(
        self, client_three_retries: SDLQueryClient
    ) -> None:
        """Test that http_max_retries=3 results in exactly 4 attempts (1 initial + 3 retries).

        Default configuration: 3 retries = 4 total attempts.
        """
        assert client_three_retries.http_max_retries == 3

        # Verify the retry policy is configured correctly
        # stop_after_attempt(4) means: 1 initial attempt + 3 retries = 4 attempts
        retry_policy = client_three_retries.retry_policy
        stop_policy = retry_policy.stop
        assert hasattr(stop_policy, "max_attempt_number")
        assert stop_policy.max_attempt_number == 4

    @pytest.mark.respx(base_url="https://test.example.test")
    async def test_zero_retries_attempts_exactly_once_on_failure(
        self,
        client_zero_retries: SDLQueryClient,
        auth_token: str,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test that with 0 retries, a failing request is attempted exactly once.

        This verifies the fix prevents UnboundLocalError when http_max_retries=0
        and ensures the request is attempted (not skipped).
        """
        # Mock a failing request
        route = respx_mock.post("/sdl/v2/api/queries").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        # Attempt the request - should fail after exactly 1 attempt
        with pytest.raises(httpx.HTTPStatusError):
            await client_zero_retries.submit(
                auth_token=auth_token,
                start_time="1h",
                end_time="now",
            )

        # Verify the request was made exactly once (no retries)
        assert route.call_count == 1

    @pytest.mark.respx(base_url="https://test.example.test")
    async def test_one_retry_attempts_exactly_twice_on_failure(
        self,
        client_one_retry: SDLQueryClient,
        auth_token: str,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test that with 1 retry, a failing request is attempted exactly twice."""
        # Mock a failing request
        route = respx_mock.post("/sdl/v2/api/queries").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        # Attempt the request - should fail after exactly 2 attempts (1 initial + 1 retry)
        with pytest.raises(httpx.HTTPStatusError):
            await client_one_retry.submit(
                auth_token=auth_token,
                start_time="1h",
                end_time="now",
            )

        # Verify the request was made exactly twice (1 retry)
        assert route.call_count == 2

    @pytest.mark.respx(base_url="https://test.example.test")
    async def test_three_retries_attempts_exactly_four_times_on_failure(
        self,
        client_three_retries: SDLQueryClient,
        auth_token: str,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test that with 3 retries, a failing request is attempted exactly four times."""
        # Mock a failing request
        route = respx_mock.post("/sdl/v2/api/queries").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        # Attempt the request - should fail after exactly 4 attempts (1 initial + 3 retries)
        with pytest.raises(httpx.HTTPStatusError):
            await client_three_retries.submit(
                auth_token=auth_token,
                start_time="1h",
                end_time="now",
            )

        # Verify the request was made exactly four times (3 retries)
        assert route.call_count == 4

    @pytest.mark.respx(base_url="https://test.example.test")
    async def test_zero_retries_succeeds_on_first_attempt(
        self,
        client_zero_retries: SDLQueryClient,
        auth_token: str,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test that with 0 retries, a successful request on first attempt works correctly."""
        # Mock a successful response
        route = respx_mock.post("/sdl/v2/api/queries").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "test-query-123",
                    "stepsCompleted": 0,
                    "totalSteps": 1,
                },
                headers={"X-Dataset-Query-Forward-Tag": "forward-tag-123"},
            )
        )

        # Make the request - should succeed on first attempt
        response, forward_tag = await client_zero_retries.submit(
            auth_token=auth_token,
            start_time="1h",
            end_time="now",
        )

        # Verify the response is valid
        assert response.id == "test-query-123"
        assert forward_tag == "forward-tag-123"

        # Verify the request was made exactly once (no retries needed)
        assert route.call_count == 1

    @pytest.mark.respx(base_url="https://test.example.test")
    async def test_three_retries_succeeds_on_second_attempt(
        self,
        client_three_retries: SDLQueryClient,
        auth_token: str,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test that with 3 retries, request succeeds if second attempt works."""
        # Mock: first attempt fails, second succeeds
        route = respx_mock.post("/sdl/v2/api/queries").mock(
            side_effect=[
                httpx.Response(500, json={"error": "Server error"}),
                httpx.Response(
                    200,
                    json={
                        "id": "test-query-456",
                        "stepsCompleted": 0,
                        "totalSteps": 1,
                    },
                    headers={"X-Dataset-Query-Forward-Tag": "forward-tag-456"},
                ),
            ]
        )

        # Make the request - should succeed on second attempt
        response, forward_tag = await client_three_retries.submit(
            auth_token=auth_token,
            start_time="1h",
            end_time="now",
        )

        # Verify the response is valid
        assert response.id == "test-query-456"
        assert forward_tag == "forward-tag-456"

        # Verify the request was attempted twice (1 failure + 1 success)
        assert route.call_count == 2


class TestRetryPolicyRegression:
    """Regression tests to prevent retry policy bugs."""

    def test_regression_zero_retries_must_not_cause_unbound_error(self, base_url: str) -> None:
        """Regression test: http_max_retries=0 must not cause UnboundLocalError.

        Previously, with http_max_retries=0, the retry loop would never execute,
        leaving the `res` variable unbound and causing UnboundLocalError when
        trying to return it.

        The fix uses stop_after_attempt(self.http_max_retries + 1) to ensure
        at least one attempt is made.
        """
        # This should not raise an error during client initialization
        client = create_client_with_retries(base_url, http_max_retries=0)

        try:
            # Verify the retry policy is configured to make at least one attempt
            stop_policy = client.retry_policy.stop
            assert hasattr(stop_policy, "max_attempt_number")
            assert stop_policy.max_attempt_number >= 1
        finally:
            if not client.is_closed():
                import asyncio

                asyncio.run(client.close())

    def test_regression_max_retries_must_mean_retries_not_attempts(self, base_url: str) -> None:
        """Regression test: http_max_retries should control retries, not attempts.

        Previously, stop_after_attempt(self.http_max_retries) was used, which
        meant http_max_retries=3 resulted in only 3 attempts (2 retries), not
        3 retries (4 attempts) as the setting name suggests.

        The fix uses stop_after_attempt(self.http_max_retries + 1) to match
        the semantic meaning of "max_retries".
        """
        client = create_client_with_retries(base_url, http_max_retries=3)

        try:
            # With 3 retries, we should have 4 attempts (1 initial + 3 retries)
            stop_policy = client.retry_policy.stop
            assert hasattr(stop_policy, "max_attempt_number")
            assert stop_policy.max_attempt_number == 4, (
                "REGRESSION: http_max_retries=3 should result in 4 attempts "
                "(1 initial + 3 retries), not 3 attempts"
            )
        finally:
            if not client.is_closed():
                import asyncio

                asyncio.run(client.close())

    def test_config_validation_allows_zero_retries(self, base_url: str) -> None:
        """Test that configuration validation allows http_max_retries=0.

        This is a valid configuration (no retries, just one attempt) and should
        not be rejected by validation.
        """
        # This should not raise ValidationError
        settings = create_sdl_settings(
            base_url=base_url,
            auth_token="Bearer test-token",
            http_max_retries=0,  # Valid: no retries, one attempt
        )

        assert settings.http_max_retries == 0
