# SDL Library

A Python library for interacting with the SentinelOne SDL (Singularity Data Lake) Query API, enabling execution of PowerQueries against the SDL backend.

## Overview

This library provides both low-level and high-level interfaces for SDL API interaction, with comprehensive query lifecycle management, error handling, and resource cleanup.

## Installation

```bash
pip install purple-mcp
```

## Quick Start

```python
import asyncio
from datetime import timedelta
from purple_mcp.libs.sdl import (
    SDLPowerQueryHandler,
    SDLPQResultType,
    create_sdl_settings
)

async def main():
    # Configure SDL settings
    settings = create_sdl_settings(
        base_url="https://your-console.sentinelone.net/sdl",
        auth_token="Bearer your-token"
    )
    
    # Create handler
    handler = SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings
    )
    
    # Execute PowerQuery
    await handler.submit_powerquery(
        start_time=timedelta(hours=24),
        end_time=timedelta(hours=0),
        query="| group count() by event.type | sort -count",
        result_type=SDLPQResultType.TABLE
    )
    
    # Wait for results
    results = await handler.poll_until_complete()
    print(f"Query completed with {results.match_count} matches")

asyncio.run(main())
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Comprehensive usage examples and patterns
- **[API Reference](docs/API.md)** - Complete API documentation
- **[Configuration](docs/CONFIG.md)** - Configuration options and settings

## Key Components

- **SDLQueryClient**: Low-level HTTP client for direct SDL API interaction
- **SDLHandler**: Abstract base class for query lifecycle management
- **SDLPowerQueryHandler**: High-level interface for PowerQuery execution
- **Configuration System**: Type-safe configuration with validation and defaults

## Key Features

- **Query Lifecycle Management**: Automatic handling of submit, poll, and cleanup
- **Resource Management**: Proper cleanup with context managers and error handling
- **Configuration**: Explicit, type-safe configuration with environment support
- **Error Handling**: Comprehensive exception hierarchy for different error types
- **Polling**: Smart polling with configurable timeouts and intervals

## Architecture

The library follows a layered architecture:
1. **SDLQueryClient**: Direct HTTP API communication
2. **SDLHandler**: Query lifecycle management and polling
3. **SDLPowerQueryHandler**: PowerQuery-specific functionality

## Contributing

This library follows the purple-mcp project's contribution guidelines. See the main project's CONTRIBUTING.md for details.