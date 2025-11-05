"""Purple AI client library."""

from purple_mcp.libs.purple_ai.client import (
    PurpleAIClient,
    PurpleAIResultType,
    ask_purple,
    sync_ask_purple,
)
from purple_mcp.libs.purple_ai.config import (
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIUserDetails,
)
from purple_mcp.libs.purple_ai.exceptions import (
    PurpleAIClientError,
    PurpleAIConfigError,
    PurpleAIError,
    PurpleAIGraphQLError,
    PurpleAISchemaError,
)

__all__ = [
    "PurpleAIClient",
    "PurpleAIClientError",
    "PurpleAIConfig",
    "PurpleAIConfigError",
    "PurpleAIConsoleDetails",
    "PurpleAIError",
    "PurpleAIGraphQLError",
    "PurpleAIResultType",
    "PurpleAISchemaError",
    "PurpleAIUserDetails",
    "ask_purple",
    "sync_ask_purple",
]
