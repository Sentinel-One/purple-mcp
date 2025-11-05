# SDL API Reference

Complete reference for the SDL Library API.

## SDLQueryClient

Low-level HTTP client for direct SDL API communication.

### Constructor
```python
SDLQueryClient(base_url: str, settings: SDLSettings)
```

**Parameters:**
- `base_url` (str): Base URL for SDL API
- `settings` (SDLSettings, optional): Configuration settings

### Context Manager Support
```python
async with SDLQueryClient(base_url, settings) as client:
    # Client operations
    pass
```

### Methods

#### `submit(auth_token: str, start_time: str, end_time: str, pq: SDLPQAttributes, query_priority: SDLQueryPriority) -> tuple[SDLQueryResponse, str]`
Submit a PowerQuery to the SDL API.

**Parameters:**
- `auth_token` (str): Bearer token for authentication
- `start_time` (str): Query start time (e.g., "24h", "2023-01-01T00:00:00Z")
- `end_time` (str): Query end time (e.g., "12h", "2023-01-01T12:00:00Z") 
- `pq` (SDLPQAttributes): PowerQuery attributes
- `query_priority` (SDLQueryPriority): Query execution priority

**Returns:** Tuple of (SDLQueryResponse, forward_tag)

#### `ping_query(auth_token: str, query_id: str, x_dataset_query_forward_tag: str) -> SDLQueryResponse`
Check query status and retrieve results.

**Parameters:**
- `auth_token` (str): Bearer token for authentication
- `query_id` (str): Unique query identifier
- `x_dataset_query_forward_tag` (str): Forward routing tag

**Returns:** SDLQueryResponse with status and results

#### `delete_query(auth_token: str, query_id: str, x_dataset_query_forward_tag: str) -> bool`
Delete a completed query to free server resources.

**Parameters:**
- `auth_token` (str): Bearer token for authentication
- `query_id` (str): Unique query identifier
- `x_dataset_query_forward_tag` (str): Forward routing tag

**Returns:** True if successfully deleted

#### `close()`
Close the HTTP client and cleanup resources.

#### `is_closed() -> bool`
Check if the client is closed.

**Returns:** True if client is closed

## SDLHandler (Abstract Base Class)

High-level interface for query lifecycle management.

### Constructor
```python
SDLHandler(auth_token: str, base_url: str, settings: SDLSettings | None = None)
```

### Abstract Methods

#### `submit_query(**kwargs) -> None`
Submit a query (implementation-specific).

#### `get_results() -> Any`
Get query results (implementation-specific).

### Concrete Methods

#### `poll_until_complete() -> SDLResultData`
Poll until query completion and return results.

**Note:** This method takes no parameters. Configure timeouts via:
- `SDLSettings.default_poll_timeout_ms` when creating settings
- `poll_results_timeout_ms` parameter in handler constructor
- `poll_interval_ms` parameter in handler constructor

**Returns:** Query results as `SDLResultData`

#### `is_result_partial() -> bool`
Check if the last query results were partial.

**Returns:** True if results are incomplete

#### `close()`
Close handler and cleanup resources.

## SDLPowerQueryHandler

Specialized handler for PowerQuery execution.

### Constructor
```python
SDLPowerQueryHandler(auth_token: str, base_url: str, settings: SDLSettings, poll_results_timeout_ms: int | None = None, poll_interval_ms: float | None = None)
```

### Methods

#### `submit_powerquery(start_time: timedelta, end_time: timedelta, query: str, result_type: SDLPQResultType = SDLPQResultType.TABLE, frequency: SDLPQFrequency = SDLPQFrequency.LOW, query_priority: SDLQueryPriority = SDLQueryPriority.LOW) -> None`
Submit a PowerQuery for execution.

**Parameters:**
- `start_time` (timedelta): Time offset from now for query start
- `end_time` (timedelta): Time offset from now for query end
- `query` (str): PowerQuery string
- `result_type` (SDLPQResultType): Expected result type (currently only TABLE is supported)
- `frequency` (SDLPQFrequency): Query frequency hint (LOW or HIGH)
- `query_priority` (SDLQueryPriority): Execution priority (LOW or HIGH)

#### `get_results() -> SDLPowerQueryResult`
Get the PowerQuery results.

**Returns:** SDLPowerQueryResult with columns, values, and metadata

## Configuration

### SDLSettings

Configuration class with type validation.

#### Fields
- `base_url: str` - Base URL for SDL API
- `auth_token: str` - Authentication token (Bearer format)
- `http_timeout: int = 30` - HTTP request timeout in seconds
- `max_timeout_seconds: int = 30` - Maximum timeout for operations
- `http_max_retries: int = 3` - Maximum HTTP request retries
- `skip_tls_verify: bool = False` - Skip TLS verification (not recommended)
- `default_poll_timeout_ms: int = 30000` - Default polling timeout
- `default_poll_interval_ms: int = 100` - Default polling interval
- `max_query_results: int = 10000` - Maximum results to retrieve
- `query_ttl_seconds: int = 300` - Query time-to-live

### `create_sdl_settings(**kwargs) -> SDLSettings`
Factory function to create SDL settings with validation.

**Parameters:** Any SDLSettings field as keyword argument

**Returns:** Configured SDLSettings instance



## Data Models

### Core Models

#### `SDLPQAttributes`
PowerQuery execution attributes.

**Fields:**
- `query: str` - PowerQuery string
- `result_type: SDLPQResultType` - Expected result type
- `frequency: SDLPQFrequency` - Query frequency

#### `SDLQueryResponse`
Response from SDL API query operations.

**Fields:**
- `id: str` - Unique query identifier
- `steps_completed: int` - Number of completed processing steps
- `total_steps: int` - Total processing steps required
- `results: list` - Query results (if available)
- `match_count: int` - Number of matches found

#### `SDLPowerQueryResult`
Processed PowerQuery results.

**Fields:**
- `columns: list[str]` - Result column names
- `values: list[list]` - Result data rows
- `match_count: int` - Number of matches
- `metadata: dict` - Additional result metadata

### Enums

#### `SDLPQResultType`
Expected PowerQuery result types.

**Currently Supported Values:**
- `TABLE` - Tabular results with columns/rows (default and recommended)

**Note:** Only `TABLE` result type is currently supported by the PowerQuery handler. Attempting to use other result types will raise an `SDLHandlerError`.

**Future Enhancements:**
The enum also defines `PLOT` for plot-based results, but this is not yet supported by the handler implementation.

#### `SDLPQFrequency`
Query execution frequency hints.

**Currently Supported Values:**
- `LOW` - Infrequent queries (default, recommended)
- `HIGH` - High frequency queries

#### `SDLQueryPriority`
Query execution priority levels.

**Currently Supported Values:**
- `LOW` - Low priority execution (default, recommended)
- `HIGH` - High priority execution

## Exception Hierarchy

**SDL-specific exceptions (raised during SDL operations):**
- `SDLError` - Base exception for all SDL errors
- `SDLClientError` - HTTP client errors
- `SDLHandlerError` - Handler-level errors (includes timeout and query execution errors)
- `SDLMalformedResponseError` - Malformed response errors

**Configuration validation exceptions:**
- `pydantic.ValidationError` - Raised by `create_sdl_settings()` when configuration parameters fail validation

### Example Error Handling

```python
from pydantic import ValidationError
from purple_mcp.libs.sdl import SDLHandlerError, create_sdl_settings

# Configuration validation raises pydantic.ValidationError
try:
    settings = create_sdl_settings(
        base_url="https://console.example.com/sdl",
        auth_token="token"
    )
except ValidationError as e:
    print(f"Configuration validation error: {e}")

# Runtime SDL operations raise SDL-specific exceptions
try:
    results = await handler.poll_until_complete()
except SDLHandlerError as e:
    print(f"Handler error (may include timeouts): {e}")
```

## Time Handling

### Time Format Support

The SDL API supports multiple time formats:

#### Relative Times
- `"24h"` - 24 hours ago
- `"7d"` - 7 days ago  
- `"30m"` - 30 minutes ago

#### Absolute Times
- `"2023-01-01T00:00:00Z"` - ISO 8601 format
- `"2023-01-01 00:00:00"` - Standard datetime format

#### Timedelta Objects
```python
from datetime import timedelta

# Using timedelta (recommended)
start_time = timedelta(hours=24)  # 24 hours ago
end_time = timedelta(hours=0)     # Now
```

### Time Conversion Utilities

#### `parse_time_param(time_param: datetime | timedelta) -> str`
Parse datetime or timedelta objects into millisecond timestamp strings for SDL APIs.

**Parameters:**
- `time_param` (datetime | timedelta): Timezone-aware datetime or timedelta offset

**Returns:** Time in milliseconds since epoch as a string

**Raises:**
- `ValueError`: If datetime is timezone-naive

```python
from purple_mcp.libs.sdl.utils import parse_time_param
from datetime import datetime, timedelta, timezone

# Convert absolute time (timezone-aware datetime required)
now_ms = parse_time_param(datetime.now(timezone.utc))

# Convert relative offset (last 24 hours)
since_ms = parse_time_param(timedelta(hours=24))
```