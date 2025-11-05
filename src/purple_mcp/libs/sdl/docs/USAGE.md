# SDL Usage Guide

Comprehensive usage examples and patterns for the SDL Library.

## Getting Started

### Basic Setup

```python
import asyncio
from datetime import timedelta
from purple_mcp.libs.sdl import (
    SDLPowerQueryHandler,
    SDLPQResultType,
    create_sdl_settings
)

async def main():
    # Create configuration
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
    
    # Your SDL operations here
    
asyncio.run(main())
```

## Using SDLPowerQueryHandler (Recommended)

### Simple Query Execution

```python
async def execute_simple_query():
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="Bearer your-token"
    )
    
    handler = SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings
    )
    
    try:
        # Submit query for last 24 hours
        await handler.submit_powerquery(
            start_time=timedelta(hours=24),
            end_time=timedelta(hours=0),
            query="| group count() by event.type | sort -count",
            result_type=SDLPQResultType.TABLE
        )
        
        # Wait for completion and get results
        results = await handler.poll_until_complete()
        
        if not handler.is_result_partial():
            print(f"Query completed successfully!")
            print(f"Matches found: {results.match_count}")
            print(f"Columns: {results.columns}")
            
            # Print results table
            for row in results.values:
                print(f"  {dict(zip(results.columns, row))}")
        else:
            print("Warning: Results are partial")
            
    except Exception as e:
        print(f"Query failed: {e}")
    finally:
        await handler.close()
```

### Query with Custom Timeouts

```python
async def query_with_custom_timeout():
    # Option 1: Configure timeout via SDLSettings
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="Bearer your-token",
        default_poll_timeout_ms=120000,  # 2 minutes default
        default_poll_interval_ms=1000    # Check every second
    )

    # Option 2: Override timeout in handler constructor for specific queries
    handler = SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings,
        poll_results_timeout_ms=180000,  # 3 minutes for complex queries
        poll_interval_ms=1000            # Check every second
    )

    try:
        await handler.submit_powerquery(
            start_time=timedelta(days=7),  # Last week
            end_time=timedelta(hours=0),
            query="| filter event.type == 'Process Created' | group count() by event.process.name | sort -count | limit 10"
        )

        # poll_until_complete() uses the timeout configured above
        results = await handler.poll_until_complete()

        print(f"Top processes: {results.match_count} found")
        for row in results.values:
            process_name, count = row
            print(f"  {process_name}: {count}")

    finally:
        await handler.close()
```

### Using TABLE Result Type

```python
from purple_mcp.libs.sdl import SDLPowerQueryHandler, SDLPQResultType, create_sdl_settings

async def query_with_table_results():
    """
    Note: Currently only TABLE result type is supported.
    PLOT result type is defined in the enum but not yet supported by the handler.
    """
    # Create SDL settings
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="Bearer your-token"
    )

    # Initialize handler with settings
    handler = SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings
    )

    try:
        # Table results (aggregated data)
        await handler.submit_powerquery(
            start_time=timedelta(hours=24),
            end_time=timedelta(hours=0),
            query="| group count() by event.severity | sort -count",
            result_type=SDLPQResultType.TABLE  # Currently the only supported type
        )

        table_results = await handler.poll_until_complete()
        print("Severity breakdown:")
        for row in table_results.values:
            severity, count = row
            print(f"  {severity}: {count}")

        # For individual events, use TABLE with appropriate query
        await handler.submit_powerquery(
            start_time=timedelta(hours=1),
            end_time=timedelta(hours=0),
            query="| filter event.severity == 'HIGH' | limit 5",
            result_type=SDLPQResultType.TABLE  # Still use TABLE for event-level queries
        )

        event_results = await handler.poll_until_complete()
        print(f"\nHigh severity events: {event_results.match_count}")
        for row in event_results.values:
            print(f"  Event: {row}")

    finally:
        await handler.close()
```

## Using SDLQueryClient (Low-Level)

### Direct Client Usage

```python
from purple_mcp.libs.sdl import (
    SDLQueryClient,
    SDLPQAttributes,
    SDLPQResultType,
    SDLPQFrequency,
    SDLQueryPriority
)

async def use_client_directly():
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="Bearer your-token"
    )
    
    # Use context manager for automatic cleanup
    async with SDLQueryClient(settings.base_url, settings=settings) as client:
        # Submit query
        response, forward_tag = await client.submit(
            auth_token=settings.auth_token,
            start_time="24h",  # 24 hours ago
            end_time="0h",     # Now
            pq=SDLPQAttributes(
                query="| group count() by event.type",
                result_type=SDLPQResultType.TABLE,
                frequency=SDLPQFrequency.LOW
            ),
            query_priority=SDLQueryPriority.LOW
        )
        
        query_id = response.id
        print(f"Query submitted: {query_id}")
        
        # Poll for results
        while True:
            ping_response = await client.ping_query(
                auth_token=settings.auth_token,
                query_id=query_id,
                x_dataset_query_forward_tag=forward_tag
            )
            
            print(f"Progress: {ping_response.steps_completed}/{ping_response.total_steps}")
            
            if ping_response.steps_completed >= ping_response.total_steps:
                print("Query completed!")
                print(f"Results: {len(ping_response.results)} items")
                
                # Process results
                for result in ping_response.results:
                    print(f"  {result}")
                
                # Clean up query
                await client.delete_query(
                    auth_token=settings.auth_token,
                    query_id=query_id,
                    x_dataset_query_forward_tag=forward_tag
                )
                break
            
            # Wait before next poll
            await asyncio.sleep(1)
```

### Manual Resource Management

```python
async def manual_client_management():
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="Bearer your-token"
    )
    
    client = SDLQueryClient(settings.base_url, settings=settings)
    
    try:
        # Submit and process query
        response, forward_tag = await client.submit(
            auth_token=settings.auth_token,
            start_time="1h",
            end_time="0h",
            pq=SDLPQAttributes(
                query="| limit 10",
                result_type=SDLPQResultType.TABLE,  # Currently only TABLE is supported
                frequency=SDLPQFrequency.LOW
            ),
            query_priority=SDLQueryPriority.LOW
        )
        
        # Process results...
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Always close the client
        await client.close()
```

## Advanced Usage Patterns

### Batch Query Processing

```python
async def process_multiple_queries():
    """Execute multiple queries in sequence."""
    
    queries = [
        ("Security Events", "| filter event.category == 'security' | group count() by event.severity"),
        ("Network Traffic", "| filter event.type == 'network' | group count() by event.protocol"),
        ("Process Activity", "| filter event.type == 'process' | group count() by event.action")
    ]
    
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="Bearer your-token"
    )
    
    results = {}
    
    for name, query in queries:
        handler = SDLPowerQueryHandler(
            auth_token=settings.auth_token,
            base_url=settings.base_url,
            settings=settings
        )
        
        try:
            print(f"Executing: {name}")
            await handler.submit_powerquery(
                start_time=timedelta(hours=24),
                end_time=timedelta(hours=0),
                query=query
            )
            
            query_results = await handler.poll_until_complete()
            results[name] = query_results
            
            print(f"  Completed: {query_results.match_count} matches")
            
        except Exception as e:
            print(f"  Failed: {e}")
            results[name] = None
            
        finally:
            await handler.close()
    
    return results
```

### Query with Progress Tracking

```python
async def query_with_progress():
    """Execute query with detailed progress tracking."""

    # Configure poll interval for more frequent progress checks
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="Bearer your-token",
        default_poll_timeout_ms=300000,  # 5 minute timeout
        default_poll_interval_ms=100     # Check every 100ms
    )

    handler = SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings
    )

    try:
        print("Submitting complex query...")
        await handler.submit_powerquery(
            start_time=timedelta(days=30),  # Large time range
            end_time=timedelta(hours=0),
            query="| group count() by event.type, event.severity | sort -count",
            result_type=SDLPQResultType.TABLE
        )

        # Manual polling with progress updates
        start_time = asyncio.get_event_loop().time()

        while not handler.is_query_completed():
            # Ping for status update
            await handler.ping_query()

            # Show progress
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            progress = (handler.steps_completed / handler.total_steps * 100) if handler.total_steps > 0 else 0
            print(f"Processing... {progress:.1f}% complete ({elapsed:.1f}s elapsed)")

            # Wait before next check
            await asyncio.sleep(2)

        # Get final results
        # Note: poll_until_complete() takes no parameters; timeouts configured above
        results = await handler.poll_until_complete()

        # Query completed
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - start_time
        print(f"Query completed in {elapsed:.2f} seconds")
        print(f"Results: {results.match_count} matches")

    finally:
        await handler.close()
```

### Time Range Analysis

```python
async def analyze_time_ranges():
    """Analyze data across different time ranges."""
    
    time_ranges = [
        ("Last Hour", timedelta(hours=1)),
        ("Last Day", timedelta(days=1)),
        ("Last Week", timedelta(days=7)),
        ("Last Month", timedelta(days=30))
    ]
    
    query_template = "| filter event.severity == 'HIGH' | group count()"
    
    for name, duration in time_ranges:
        handler = SDLPowerQueryHandler(
            auth_token="Bearer your-token",
            base_url="https://console.example.com/sdl"
        )
        
        try:
            await handler.submit_powerquery(
                start_time=duration,
                end_time=timedelta(hours=0),
                query=query_template
            )
            
            results = await handler.poll_until_complete()
            
            if results.values:
                count = results.values[0][0]  # First column, first row
                print(f"{name}: {count} high severity events")
            else:
                print(f"{name}: No events found")
                
        except Exception as e:
            print(f"{name}: Error - {e}")
            
        finally:
            await handler.close()
```

### Error Handling Patterns

```python
from pydantic import ValidationError
from purple_mcp.libs.sdl import SDLHandlerError, create_sdl_settings

async def robust_query_execution():
    """Execute queries with comprehensive error handling."""

    # Configuration validation happens here and raises ValidationError
    # Note: Configure timeouts via default_poll_timeout_ms in settings
    try:
        settings = create_sdl_settings(
            base_url="https://console.example.com/sdl",
            auth_token="your-token",
            default_poll_timeout_ms=60000  # 60 second timeout
        )
    except ValidationError as e:
        print(f"Configuration validation error: {e}")
        return

    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        # Create a fresh handler for each attempt
        # Note: Handlers cannot be reused after errors due to state management
        handler = SDLPowerQueryHandler(
            auth_token=settings.auth_token,
            base_url=settings.base_url,
            settings=settings,
            poll_results_timeout_ms=60000  # Override the default timeout
        )

        try:
            print(f"Attempt {attempt + 1}/{max_retries}")

            await handler.submit_powerquery(
                start_time=timedelta(hours=24),
                end_time=timedelta(hours=0),
                query="| group count() by event.type"
            )

            # Note: poll_until_complete() takes no parameters
            # Timeout is configured via SDLSettings or handler constructor
            results = await handler.poll_until_complete()

            print("Query successful!")
            print(f"Results: {results.match_count} matches")
            break

        except SDLHandlerError as e:
            # SDLHandlerError covers timeouts and other handler-level errors
            print(f"Handler error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                print("All attempts failed")

        except Exception as e:
            print(f"Unexpected error: {e}")
            break

        finally:
            # Always clean up resources after each attempt
            await handler.close()
```

## Query Optimization

### Efficient Query Design

```python
async def optimized_queries():
    """Examples of optimized SDL queries."""
    
    handler = SDLPowerQueryHandler(
        auth_token="Bearer your-token",
        base_url="https://console.example.com/sdl"
    )
    
    try:
        # ✅ Good: Filter early to reduce data processing
        await handler.submit_powerquery(
            start_time=timedelta(hours=6),  # Reasonable time range
            end_time=timedelta(hours=0),
            query="| filter event.severity in ('HIGH', 'CRITICAL') | group count() by event.type | limit 10"
        )
        
        results = await handler.poll_until_complete()
        print(f"Optimized query: {results.match_count} results")
        
        # ❌ Avoid: Large time ranges without filtering
        # This would be slow and resource-intensive:
        # query = "| group count() by event.type"  # No filtering
        # start_time = timedelta(days=365)  # Entire year
        
    finally:
        await handler.close()
```

### Query Performance Tips

```python
async def performance_tips():
    """Demonstrate query performance best practices."""
    
    # 1. Use appropriate time ranges
    print("1. Reasonable time ranges:")
    short_range_query = "| filter event.type == 'authentication' | group count() by event.outcome"
    
    # 2. Filter early in the pipeline
    print("2. Early filtering:")
    filtered_query = "| filter event.severity == 'HIGH' | filter event.category == 'security' | group count()"
    
    # 3. Use limits to control result size
    print("3. Limited results:")
    limited_query = "| group count() by event.source.ip | sort -count | limit 20"
    
    # 4. Use TABLE result type (currently the only supported type)
    print("4. Use TABLE result type:")
    # TABLE works for both aggregated and event-level queries
    # The query determines whether you get aggregated or individual event data
    
    handler = SDLPowerQueryHandler(
        auth_token="Bearer your-token",
        base_url="https://console.example.com/sdl"
    )
    
    try:
        # Execute performance-optimized query
        await handler.submit_powerquery(
            start_time=timedelta(hours=4),  # 4 hours - reasonable range
            end_time=timedelta(hours=0),
            query=filtered_query,  # Pre-filtered
            result_type=SDLPQResultType.TABLE  # Appropriate type
        )
        
        results = await handler.poll_until_complete()
        print(f"Performance query completed: {results.match_count} results")
        
    finally:
        await handler.close()
```

## Configuration-Based Usage

### Environment-Specific Handlers

```python
def get_sdl_handler(environment: str):
    """Create SDL handler for specific environment."""
    
    configs = {
        "development": create_sdl_settings(
            base_url="https://dev-console.example.com/sdl",
            auth_token=os.getenv("SDL_DEV_TOKEN"),
            http_timeout=60,
            default_poll_timeout_ms=120000
        ),
        "production": create_sdl_settings(
            base_url="https://prod-console.example.com/sdl",
            auth_token=os.getenv("SDL_PROD_TOKEN"),
            http_timeout=30,
            default_poll_timeout_ms=60000
        )
    }
    
    settings = configs[environment]
    
    return SDLPowerQueryHandler(
        auth_token=settings.auth_token,
        base_url=settings.base_url,
        settings=settings
    )

# Usage
async def environment_specific_query():
    # Get handler for current environment
    env = os.getenv("ENVIRONMENT", "development")
    handler = get_sdl_handler(env)
    
    try:
        await handler.submit_powerquery(
            start_time=timedelta(hours=24),
            end_time=timedelta(hours=0),
            query="| group count() by event.type"
        )
        
        results = await handler.poll_until_complete()
        print(f"Environment {env}: {results.match_count} results")
        
    finally:
        await handler.close()
```

## Testing Patterns

### Mock Testing

```python
from unittest.mock import AsyncMock, patch

async def test_sdl_operations():
    """Example of testing SDL operations."""
    
    # Mock the client responses
    mock_response = Mock()
    mock_response.id = "test-query-id"
    mock_response.steps_completed = 1
    mock_response.total_steps = 1
    mock_response.results = [{"event_type": "test", "count": 5}]
    mock_response.match_count = 1
    
    with patch('purple_mcp.libs.sdl.SDLQueryClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.submit.return_value = (mock_response, "test-forward-tag")
        mock_client.ping_query.return_value = mock_response
        
        # Test the handler
        handler = SDLPowerQueryHandler(
            auth_token="Bearer test-token",
            base_url="https://test.example.com/sdl"
        )
        
        await handler.submit_powerquery(
            start_time=timedelta(hours=1),
            end_time=timedelta(hours=0),
            query="| group count()"
        )
        
        results = await handler.poll_until_complete()
        
        assert results.match_count == 1
        assert len(results.values) == 1
        print("✅ SDL test passed")
```

## Debugging and Logging

### Enable Debug Logging

```python
import logging

# Enable SDL debug logging
logging.getLogger("purple_mcp.libs.sdl").setLevel(logging.DEBUG)

# This will show:
# - Configuration validation
# - HTTP requests and responses
# - Query lifecycle events
# - Error details
```

### Custom Logging

```python
async def query_with_logging():
    """Execute query with custom logging."""
    
    logger = logging.getLogger("my_app.sdl")
    
    handler = SDLPowerQueryHandler(
        auth_token="Bearer your-token",
        base_url="https://console.example.com/sdl"
    )
    
    try:
        logger.info("Starting SDL query")
        
        await handler.submit_powerquery(
            start_time=timedelta(hours=24),
            end_time=timedelta(hours=0),
            query="| group count() by event.type"
        )
        
        logger.info("Query submitted, waiting for results")
        
        results = await handler.poll_until_complete()
        
        logger.info(f"Query completed: {results.match_count} matches")
        
        return results
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise
        
    finally:
        await handler.close()
```