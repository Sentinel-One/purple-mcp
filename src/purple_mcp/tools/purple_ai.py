"""Purple AI MCP tool implementation.

This module defines the `purple_ai` MCP tool which acts as a thin wrapper
around SentinelOne Purple AI, exposing it to FastMCP clients.  The helper
collects configuration, performs authentication, and relays the user's
query to the underlying GraphQL API before streaming back a plaintext
answer.

Key Components:
    - purple_ai(): Asynchronous entry-point registered as an MCP tool.
    - PurpleAIConfig / PurpleAI*Details: Data-classes describing runtime
      configuration and user / console context.

Usage:
    The tool is automatically registered when `purple_mcp.server` is
    imported but can also be called directly for unit-testing:

    ```python
    from purple_mcp.tools.purple_ai import purple_ai

    answer = await purple_ai("What threats affected my estate last week?")
    print(answer)
    ```

Architecture:
    1. Resolve runtime configuration via `purple_mcp.config.get_settings()`.
    2. Build the strongly-typed config objects required by
       `purple_mcp.libs.purple_ai`.
    3. Delegate the network call to `ask_purple`, returning the raw message
       so that transport-layer formatting is handled by FastMCP.

Dependencies:
    - purple_mcp.libs.purple_ai: Encapsulates all networking and GraphQL
      specifics.
    - fastmcp: Registers the callable as an MCP tool (handled by the server).
    - pydantic-settings (indirect): Provides the strongly-typed Settings
      object retrieved by `get_settings()`.

Raises:
    RuntimeError: When settings are missing or invalid prior to issuing the
        request.
    PurpleAIClientError: When the Purple AI request fails or returns an error
        response.
    PurpleAIGraphQLError: When there is a GraphQL-level error in the response.
"""

from textwrap import dedent
from typing import Final

from purple_mcp.config import get_settings
from purple_mcp.libs.purple_ai import (
    PurpleAIClientError,
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIGraphQLError,
    PurpleAIUserDetails,
    ask_purple,
)

PURPLE_AI_DESCRIPTION: Final[str] = dedent(
    """
    Interact with SentinelOne's Purple AI, a cybersecurity assistant that helps you investigate threats, generate PowerQueries, and answer questions about SentinelOne. Purple AI understands natural language and converts your questions into structured security queries, or answers in plain language.

    What Purple AI can do:
    - Generate and explain PowerQueries for threat hunting and detection
    - Help answer questions using threat intelligence and behavioral signals
    - Explore user, process, network, and file-based activities
    - Investigate MITRE TTPs, ransomware behavior, lateral movement, and more
    - Answer questions about SentinelOne capabilities

    What Purple AI can't do:
    - Access active alerts (use the Alerts tool for that)
    - Modify configurations or directly interact with your endpoints
    - Run the PowerQueries itself (use the PowerQuery tool to run the PQ returned by Purple AI)

    ---

    How to ask good questions

    Purple AI works best when your questions are:
    - Descriptive: Include process names, file paths, domains, ports, or usernames
    - Focused: Describe what you're trying to understand or find
    - Scoped: If helpful, include filters like time ranges, endpoint type, or OS

    Example questions:
    - Show me PowerShell processes that connected to external IPs
    - Find unsigned processes that accessed lsass.exe
    - List endpoints where the user “jsmith” logged in more than 5 times
    - Are there any reverse SSH tunnels from public IPs?
    - Find living-off-the-land binaries spawned from Microsoft Word

    DO NOT instruct Purple AI to "Generate a Powerquery to ...".  Instead, just say what you are looking for.
    Example:
        - GOOD: "Is APT-1337 in my environment?"
        - BAD: "Generate a PowerQuery to determine if APT-1337 is in my environment, including their typical tools, processes, and TTPs."
    ---

    Tips for writing questions
    - Start with verbs like: show, find, list, search
    - Add specific entities like: powershell, svchost, lolbins, ssh, .tmp files
    - Use filters like: external IPs, non-Windows folders, file size over 1GB
    - Ask about behaviors: ransomware, persistence, privilege escalation, data staging, beaconing, phishing
    - If you want a PowerQuery, specifically say "generate a powerquery for " -> Example: "Generate a PowerQuery to detect Wizard Spider threat group indicators"
    """
).strip()


async def purple_ai(query: str) -> str:
    """Ask Purple AI a question. Purple AI is a tool to answer cyber security questions.

    Args:
        query: The question to ask Purple AI.

    Returns:
        The response from Purple AI as a string.

    Raises:
        RuntimeError: If settings are not properly configured.
        PurpleAIGraphQLError: If the GraphQL query fails.
        PurpleAIClientError: For other client-level errors.
    """
    try:
        settings = get_settings()
    except Exception as e:
        raise RuntimeError(
            f"Settings not initialized. Please check your environment configuration. Error: {e}"
        ) from e

    user_details = PurpleAIUserDetails(
        account_id=settings.purple_ai_account_id,
        team_token=settings.purple_ai_team_token,
        session_id=settings.purple_ai_session_id,
        email_address=settings.purple_ai_email_address,
        user_agent=settings.purple_ai_user_agent,
        build_date=settings.purple_ai_build_date,
        build_hash=settings.purple_ai_build_hash,
    )

    console_details = PurpleAIConsoleDetails(
        base_url=settings.sentinelone_console_base_url,
        version=settings.purple_ai_console_version,
    )

    config = PurpleAIConfig(
        graphql_url=settings.graphql_full_url,
        auth_token=settings.graphql_service_token,
        user_details=user_details,
        console_details=console_details,
    )

    try:
        response_type, raw_message = await ask_purple(config, query)

        # If ask_purple returns None as the result type, it signals a transport or
        # processing failure. The raw_message contains the error description.
        if response_type is None:
            # Check if this is a known UNKNOWN error that we should handle gracefully
            error_str = str(raw_message)
            if "errorType': 'UNKNOWN'" in error_str or "'errorType': 'UNKNOWN'" in error_str:
                return "Purple AI encountered an error with this question. Please try rephrasing your question and submitting it again."

            # For other errors, raise the exception as before
            raise PurpleAIClientError(
                "Purple AI request failed",
                details=error_str,
            )

        message: str = str(raw_message)
        return message
    except (PurpleAIGraphQLError, PurpleAIClientError):
        # Re-raise typed exceptions as-is to preserve error context
        raise
