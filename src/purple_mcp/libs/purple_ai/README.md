# Purple AI Library

A Python library for interacting with SentinelOne's Purple AI assistant through GraphQL APIs.

## Overview

This library provides both async and sync interfaces for asking questions to Purple AI, SentinelOne's cybersecurity AI assistant. It handles authentication, conversation management, and response parsing.

## Installation

```bash
pip install purple-mcp
```

## Quick Start

```python
import asyncio
from purple_mcp.libs.purple_ai import (
    ask_purple,
    PurpleAIConfig,
    PurpleAIUserDetails,
    PurpleAIConsoleDetails,
)

async def main():
    # Configure Purple AI
    config = PurpleAIConfig(
        graphql_url="https://your-console.sentinelone.net/web/api/v2.1/graphql",
        auth_token="your-service-token",
        user_details=PurpleAIUserDetails(
            account_id="your-account-id",
            team_token="your-team-token",
            session_id="your-session-id",
            email_address="user@example.com",
            user_agent="PurpleAI-Client/1.0",
            build_date="2024-01-01",
            build_hash="abc123",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://your-console.sentinelone.net",
            version="1.0.0",
        ),
    )

    # Ask Purple AI a question
    result_type, response = await ask_purple("What are the latest threats in my environment?", config)
    if result_type is None:
        print(f"Error: {response}")
    else:
        print(f"Purple AI ({result_type}): {response}")

asyncio.run(main())
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage examples and patterns
- **[API Reference](docs/API.md)** - Complete API documentation  
- **[Configuration](docs/CONFIG.md)** - Configuration options and setup

## Key Features

- **Async & Sync Support**: Both async (`ask_purple`) and sync (`sync_ask_purple`) interfaces
- **Conversation Management**: Automatic conversation ID generation and management
- **Response Types**: Support for both message and PowerQuery responses
- **Configuration**: Flexible configuration with environment variable support
- **Security Validation**: Automatic validation of HTTPS URLs, tokens, and timeouts
- **Error Handling**: Comprehensive error handling for network and API issues

## Response Types

Purple AI can return two types of responses:
- **MESSAGE**: Direct text responses with analysis and recommendations
- **POWER_QUERY**: SDL PowerQuery code for further data analysis

## Authentication

The library requires a SentinelOne console service token with appropriate permissions to access the Purple AI GraphQL endpoint.

## Contributing

This library follows the purple-mcp project's contribution guidelines. See the main project's CONTRIBUTING.md for details.
