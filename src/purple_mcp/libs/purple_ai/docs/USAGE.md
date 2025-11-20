# Purple AI Usage Guide

Comprehensive usage examples and patterns for the Purple AI Library.

## Getting Started

### Basic Setup

```python
import asyncio
import os
from purple_mcp.libs.purple_ai import (
    ask_purple,
    PurpleAIConfig,
    PurpleAIUserDetails,
    PurpleAIConsoleDetails,
)

async def main():
    # Create configuration
    config = PurpleAIConfig(
        graphql_url="https://your-console.sentinelone.net/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN"),
        user_details=PurpleAIUserDetails(
            account_id=os.getenv("PURPLEMCP_PURPLE_AI_ACCOUNT_ID"),
            team_token=os.getenv("PURPLEMCP_PURPLE_AI_TEAM_TOKEN"),
            session_id=os.getenv("PURPLEMCP_PURPLE_AI_SESSION_ID"),
            email_address=os.getenv("PURPLEMCP_PURPLE_AI_EMAIL_ADDRESS"),
            user_agent="PurpleAI-Client/1.0",
            build_date="2024-01-01",
            build_hash="abc123",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url=os.getenv("PURPLEMCP_CONSOLE_BASE_URL", "https://your-console.sentinelone.net"),
            version="1.0.0",
        ),
    )

    # Ask Purple AI a question
    result_type, response = await ask_purple("What are the latest security threats?", config)
    if result_type is None:
        print(f"Error: {response}")
    else:
        print(f"Purple AI ({result_type}): {response}")

asyncio.run(main())
```

### Synchronous Usage

```python
from purple_mcp.libs.purple_ai import (
    sync_ask_purple,
    PurpleAIConfig,
    PurpleAIUserDetails,
    PurpleAIConsoleDetails,
)

# Create configuration
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

# Ask Purple AI synchronously
response = sync_ask_purple("Are there any active threats in my environment?", config)
print(f"Purple AI: {response}")
```

## Common Purple AI Questions

### Threat Intelligence

```python
async def threat_intelligence_queries():
    """Examples of threat intelligence questions."""
    
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    questions = [
        "What are the latest threats in my environment?",
        "Show me high-severity alerts from the past 24 hours",
        "Are there any indicators of APT activity?",
        "What malware families are currently active?",
        "Tell me about suspicious network activity",
    ]
    
    for question in questions:
        print(f"\nQ: {question}")
        _result_type, response = await ask_purple(question, config)
        print(f"A: {response}")
```

### System Analysis

```python
async def system_analysis_queries():
    """Examples of system analysis questions."""
    
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    questions = [
        "What processes are consuming the most resources?",
        "Show me failed authentication attempts",
        "Are there any unusual file system changes?",
        "What network connections look suspicious?",
        "Analyze recent PowerShell activity",
    ]
    
    for question in questions:
        print(f"\nQ: {question}")
        _result_type, response = await ask_purple(question, config)
        print(f"A: {response}")
```

### Incident Response

```python
async def incident_response_queries():
    """Examples of incident response questions."""
    
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    questions = [
        "What should I investigate first for this alert?",
        "Help me understand this malware detection",
        "What are the indicators of compromise for this incident?", 
        "How can I contain this threat?",
        "What remediation steps do you recommend?",
    ]
    
    for question in questions:
        print(f"\nQ: {question}")
        _result_type, response = await ask_purple(question, config)
        print(f"A: {response}")
```

## Advanced Usage Patterns

### Interactive Security Assistant

```python
async def interactive_security_assistant():
    """Create an interactive Purple AI session."""
    
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    print("🟣 Purple AI Security Assistant")
    print("Type 'quit' to exit\n")
    
    while True:
        try:
            # Get user input
            question = input("You: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not question:
                continue
            
            # Ask Purple AI
            print("🟣 Thinking...")
            _result_type, response = await ask_purple(question, config)
            print(f"Purple AI: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")

# Run the assistant
asyncio.run(interactive_security_assistant())
```

### Batch Question Processing

```python
async def process_questions_batch():
    """Process multiple questions efficiently."""
    
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    # List of questions to ask
    questions = [
        "What are the top 5 security risks in my environment?",
        "Show me recent malware detections",
        "Are there any compromised accounts?",
        "What network anomalies should I investigate?",
        "Summarize today's security events"
    ]
    
    results = []
    
    for i, question in enumerate(questions, 1):
        try:
            print(f"Processing question {i}/{len(questions)}: {question[:50]}...")

            _result_type, response = await ask_purple(question, config)
            results.append({
                'question': question,
                'response': response,
                'status': 'success'
            })
            
            # Small delay to be respectful to the API
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error processing question {i}: {e}")
            results.append({
                'question': question,
                'response': None,
                'status': 'error',
                'error': str(e)
            })
    
    # Process results
    print("\n" + "="*50)
    print("BATCH PROCESSING RESULTS")
    print("="*50)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['question']}")
        if result['status'] == 'success':
            print(f"   ✅ {result['response']}")
        else:
            print(f"   ❌ Error: {result['error']}")
    
    return results
```

### Question Templates

```python
class PurpleAITemplates:
    """Collection of reusable Purple AI question templates."""
    
    @staticmethod
    def threat_summary(time_period: str = "24 hours") -> str:
        return f"Summarize security threats from the past {time_period}"
    
    @staticmethod
    def investigate_ip(ip_address: str) -> str:
        return f"Investigate activity from IP address {ip_address}"
    
    @staticmethod
    def analyze_process(process_name: str) -> str:
        return f"Analyze the security implications of process '{process_name}'"
    
    @staticmethod
    def malware_analysis(file_hash: str) -> str:
        return f"Tell me about this file hash: {file_hash}"
    
    @staticmethod
    def user_activity(username: str) -> str:
        return f"Analyze recent activity for user '{username}'"
    
    @staticmethod
    def network_analysis(domain: str) -> str:
        return f"Analyze network connections to domain '{domain}'"

# Usage
async def use_templates():
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    # Generate questions from templates
    questions = [
        PurpleAITemplates.threat_summary("7 days"),
        PurpleAITemplates.investigate_ip("192.168.1.100"),
        PurpleAITemplates.analyze_process("powershell.exe"),
        PurpleAITemplates.user_activity("admin@company.com")
    ]
    
    for question in questions:
        _result_type, response = await ask_purple(question, config)
        print(f"Q: {question}")
        print(f"A: {response}\n")
```

## Integration Patterns

### With Logging

```python
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ask_purple_with_logging(question: str, config: PurpleAIConfig):
    """Ask Purple AI with comprehensive logging."""
    
    start_time = datetime.now()
    logger.info(f"Asking Purple AI: {question}")
    
    try:
        _result_type, response = await ask_purple(question, config)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Purple AI responded in {duration:.2f}s")
        logger.debug(f"Response: {response[:100]}...")  # Log first 100 chars
        
        return response
        
    except Exception as e:
        logger.error(f"Purple AI request failed: {e}")
        raise

# Usage
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
)

response = await ask_purple_with_logging("What threats exist?", config)
```

### With Caching

```python
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class PurpleAICache:
    """Simple in-memory cache for Purple AI responses."""
    
    def __init__(self, ttl_minutes: int = 30):
        self.cache: Dict[str, Tuple[str, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _get_key(self, question: str, config: PurpleAIConfig) -> str:
        """Generate cache key from question and config."""
        config_str = f"{config.graphql_url}:{config.auth_token[:10]}"
        combined = f"{question}:{config_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, question: str, config: PurpleAIConfig) -> Optional[str]:
        """Get cached response if available and not expired."""
        key = self._get_key(question, config)
        
        if key in self.cache:
            response, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return response
            else:
                # Expired, remove from cache
                del self.cache[key]
        
        return None
    
    def set(self, question: str, config: PurpleAIConfig, response: str):
        """Cache the response."""
        key = self._get_key(question, config)
        self.cache[key] = (response, datetime.now())
    
    def clear(self):
        """Clear all cached responses."""
        self.cache.clear()

# Global cache instance
purple_ai_cache = PurpleAICache(ttl_minutes=30)

async def ask_purple_cached(question: str, config: PurpleAIConfig) -> str:
    """Ask Purple AI with caching support."""
    
    # Check cache first
    cached_response = purple_ai_cache.get(question, config)
    if cached_response:
        print("📋 Returning cached response")
        return cached_response
    
    # Not in cache, ask Purple AI
    print("🟣 Asking Purple AI...")
    _result_type, response = await ask_purple(question, config)
    
    # Cache the response
    purple_ai_cache.set(question, config, response)
    
    return response

# Usage
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
)

# First call - will ask Purple AI
response1 = await ask_purple_cached("What threats exist?", config)

# Second call - will use cached response
response2 = await ask_purple_cached("What threats exist?", config)
```

### With Retry Logic

```python
import asyncio
import random
from typing import Optional

async def ask_purple_with_retry(
    question: str, 
    config: PurpleAIConfig,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Optional[str]:
    """Ask Purple AI with exponential backoff retry logic."""
    
    for attempt in range(max_retries):
        try:
            _result_type, response = await ask_purple(question, config)
            return response
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return None
            
            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # Add up to 10% jitter
            total_delay = delay + jitter
            
            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {total_delay:.1f} seconds...")
            
            await asyncio.sleep(total_delay)
    
    return None

# Usage
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
)

response = await ask_purple_with_retry(
    "What are the current security threats?",
    config,
    max_retries=5,
    base_delay=2.0
)

if response:
    print(f"Purple AI: {response}")
else:
    print("Could not get response from Purple AI after retries")
```

## Error Handling Patterns

### Comprehensive Error Handling

```python
import httpx
from purple_mcp.libs.purple_ai import ask_purple, PurpleAIConfig

async def robust_purple_ai_query(question: str, config: PurpleAIConfig) -> Optional[str]:
    """Ask Purple AI with comprehensive error handling."""
    
    try:
        _result_type, response = await ask_purple(question, config)
        return response
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("   Check your GraphQL URL and service token")
        return None
        
    except httpx.TimeoutException:
        print("❌ Request timed out")
        print("   Purple AI may be busy, try again later")
        return None
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ Authentication failed")
            print("   Check your service token permissions")
        elif e.response.status_code == 403:
            print("❌ Access forbidden") 
            print("   Your token may not have Purple AI access")
        elif e.response.status_code == 404:
            print("❌ GraphQL endpoint not found")
            print("   Check your console URL")
        elif e.response.status_code == 429:
            print("❌ Rate limit exceeded")
            print("   Too many requests, wait before retrying")
        else:
            print(f"❌ HTTP error {e.response.status_code}: {e}")
        return None
        
    except httpx.ConnectError:
        print("❌ Connection failed")
        print("   Check network connectivity and console URL")
        return None
        
    except KeyError as e:
        print(f"❌ Unexpected API response format: {e}")
        print("   The Purple AI API may have changed")
        return None
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

# Usage
config = PurpleAIConfig(
    graphql_url="https://console.example.com/web/api/v2.1/graphql",
    auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
)

response = await robust_purple_ai_query("What threats exist?", config)
if response:
    print(f"Success: {response}")
else:
    print("Unable to get response from Purple AI")
```

### Graceful Degradation

```python
async def security_analysis_with_fallback(indicators: list[str]):
    """Perform security analysis with Purple AI, fallback to basic analysis."""
    
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    results = {}
    
    for indicator in indicators:
        question = f"Analyze this security indicator: {indicator}"
        
        # Try Purple AI first
        try:
            response = await ask_purple(question, config)
            results[indicator] = {
                'source': 'Purple AI',
                'analysis': response
            }
            continue
            
        except Exception as e:
            print(f"Purple AI failed for {indicator}: {e}")
        
        # Fallback to basic analysis
        basic_analysis = perform_basic_analysis(indicator)
        results[indicator] = {
            'source': 'Basic Analysis',
            'analysis': basic_analysis
        }
    
    return results

def perform_basic_analysis(indicator: str) -> str:
    """Basic fallback analysis when Purple AI is unavailable."""
    
    if indicator.count('.') == 3:  # Looks like IP
        return f"IP address {indicator} - recommend checking threat intelligence feeds"
    elif '.' in indicator and len(indicator) > 4:  # Looks like domain
        return f"Domain {indicator} - recommend DNS and reputation checks"  
    elif len(indicator) in [32, 40, 64]:  # Looks like hash
        return f"File hash {indicator} - recommend malware analysis"
    else:
        return f"Unknown indicator type: {indicator} - manual analysis required"

# Usage
indicators = [
    "192.168.1.100", 
    "malicious.example.com",
    "d41d8cd98f00b204e9800998ecf8427e"
]

results = await security_analysis_with_fallback(indicators)
for indicator, result in results.items():
    print(f"\n{indicator} ({result['source']}):")
    print(f"  {result['analysis']}")
```

## Performance Optimization

### Concurrent Queries

```python
import asyncio
from typing import List, Dict

async def ask_purple_concurrent(questions: List[str], config: PurpleAIConfig) -> Dict[str, str]:
    """Ask multiple questions concurrently for better performance."""
    
    async def ask_single_question(question: str) -> tuple[str, str]:
        """Ask a single question and return (question, response) tuple."""
        try:
            response = await ask_purple(question, config)
            return question, response
        except Exception as e:
            return question, f"Error: {e}"
    
    # Create tasks for all questions
    tasks = [ask_single_question(q) for q in questions]
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    responses = {}
    for result in results:
        if isinstance(result, Exception):
            # Handle exceptions from gather
            continue
        question, response = result
        responses[question] = response
    
    return responses

# Usage
async def concurrent_threat_analysis():
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    questions = [
        "What are the current high-priority alerts?",
        "Show me recent malware detections",
        "Are there any failed authentication patterns?",
        "What network anomalies should I investigate?",
        "Summarize today's security events"
    ]
    
    print("🟣 Asking Purple AI multiple questions concurrently...")
    start_time = asyncio.get_event_loop().time()
    
    responses = await ask_purple_concurrent(questions, config)
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    print(f"✅ Completed {len(responses)} queries in {duration:.2f} seconds")
    
    for question, response in responses.items():
        print(f"\nQ: {question}")
        print(f"A: {response[:100]}..." if len(response) > 100 else f"A: {response}")
    
    return responses

# Run concurrent analysis
responses = await concurrent_threat_analysis()
```

### Request Rate Limiting

```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter for Purple AI requests."""
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests = []
    
    async def acquire(self):
        """Wait until we can make a request within rate limits."""
        now = datetime.now()
        
        # Remove old requests (older than 1 minute)
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < timedelta(minutes=1)]
        
        # If we're at the limit, wait
        if len(self.requests) >= self.requests_per_minute:
            oldest_request = min(self.requests)
            wait_until = oldest_request + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                print(f"Rate limit reached, waiting {wait_seconds:.1f} seconds...")
                await asyncio.sleep(wait_seconds)
        
        # Record this request
        self.requests.append(now)

# Global rate limiter
purple_ai_rate_limiter = RateLimiter(requests_per_minute=20)

async def ask_purple_rate_limited(question: str, config: PurpleAIConfig) -> str:
    """Ask Purple AI with rate limiting."""
    
    await purple_ai_rate_limiter.acquire()
    return await ask_purple(question, config)

# Usage
async def rate_limited_analysis():
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    questions = [f"Analyze security event {i}" for i in range(50)]  # Many questions
    
    for i, question in enumerate(questions):
        print(f"Processing question {i+1}/{len(questions)}")
        response = await ask_purple_rate_limited(question, config)
        print(f"Response: {response[:50]}...")

# Run rate-limited analysis
await rate_limited_analysis()
```

## Testing Patterns

### Mock Purple AI for Testing

```python
from unittest.mock import AsyncMock, patch
import pytest

class MockPurpleAI:
    """Mock Purple AI for testing."""
    
    def __init__(self):
        self.responses = {
            "what threats exist": "No active threats detected in your environment.",
            "show alerts": "There are 3 medium-severity alerts requiring attention.",
            "analyze ip 192.168.1.100": "IP address appears to be internal and benign."
        }
    
    async def ask(self, question: str, config) -> str:
        """Mock ask_purple function."""
        # Simple keyword matching for test responses
        for key, response in self.responses.items():
            if any(word in question.lower() for word in key.split()):
                return response
        
        return "I don't have information about that query."

# Test usage
@pytest.mark.asyncio
async def test_security_analysis():
    """Test security analysis with mock Purple AI."""
    
    mock_purple = MockPurpleAI()
    
    with patch('purple_mcp.libs.purple_ai.ask_purple', mock_purple.ask):
        config = PurpleAIConfig(
            graphql_url="https://test.example.com/web/api/v2.1/graphql",
            auth_token="test-token"
        )


        _result_type, response = await ask_purple("what threats exist", config)
        assert "No active threats" in response


        _result_type, response = await ask_purple("show alerts", config)  
        assert "3 medium-severity alerts" in response
```

### Integration Testing

```python
import os
import pytest
from purple_mcp.libs.purple_ai import ask_purple, sync_ask_purple, PurpleAIConfig

@pytest.mark.asyncio
@pytest.mark.integration
async def test_purple_ai_integration():
    """Integration test with real Purple AI (requires credentials)."""
    
    # Skip if no credentials
    if not all([os.getenv("PURPLEMCP_CONSOLE_BASE_URL"), os.getenv("PURPLEMCP_CONSOLE_TOKEN")]):
        pytest.skip("Missing PURPLEMCP_CONSOLE_BASE_URL or PURPLEMCP_CONSOLE_TOKEN for integration test")

    config = PurpleAIConfig(
        graphql_url=os.getenv("PURPLEMCP_CONSOLE_BASE_URL") + "/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    # Test async function
_result_type, response = await ask_purple("What is SentinelOne?", config)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "SentinelOne" in response
    
    # Test sync function  
    response = sync_ask_purple("What is Purple AI?", config)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.integration
def test_purple_ai_error_handling():
    """Test error handling with invalid configuration."""
    
    # Test with invalid URL
    invalid_config = PurpleAIConfig(
        graphql_url="https://invalid.example.com/web/api/v2.1/graphql",
        auth_token="invalid-token"
    )
    
    with pytest.raises(Exception):
        sync_ask_purple("Test question", invalid_config)
```

## Production Usage Patterns

### Health Check Integration

```python
async def purple_ai_health_check() -> dict:
    """Check if Purple AI is available and responding."""
    
    config = PurpleAIConfig(
        graphql_url="https://console.example.com/web/api/v2.1/graphql",
        auth_token=os.getenv("PURPLEMCP_CONSOLE_TOKEN")
    )
    
    try:
        start_time = datetime.now()
        
        # Ask a simple question to test connectivity
_result_type, response = await ask_purple("What is SentinelOne?", config)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'status': 'healthy',
            'response_time_seconds': duration,
            'response_length': len(response),
            'timestamp': start_time.isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# Usage in health check endpoint
async def api_health_check():
    """API endpoint health check including Purple AI."""
    
    health_status = {
        'service': 'security-analysis-api',
        'status': 'healthy',
        'checks': {}
    }
    
    # Check Purple AI
    purple_ai_status = await purple_ai_health_check()
    health_status['checks']['purple_ai'] = purple_ai_status
    
    if purple_ai_status['status'] != 'healthy':
        health_status['status'] = 'degraded'
    
    return health_status
```

### Configuration Management

```python
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class PurpleAISettings:
    """Centralized Purple AI settings management."""
    
    console_base_url: str
    service_token: str
    account_id: Optional[str] = None
    console_version: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    
    @classmethod
    def from_environment(cls) -> 'PurpleAISettings':
        """Create settings from environment variables."""
        
        base_url = os.getenv("PURPLEMCP_CONSOLE_BASE_URL")
        if not base_url:
            raise ValueError("PURPLEMCP_CONSOLE_BASE_URL environment variable required")

        token = os.getenv("PURPLEMCP_CONSOLE_TOKEN")
        if not token:
            raise ValueError("PURPLEMCP_CONSOLE_TOKEN environment variable required")
        
        return cls(
            console_base_url=base_url,
            service_token=token,
            account_id=os.getenv("PURPLEMCP_PURPLE_AI_ACCOUNT_ID"),
            console_version=os.getenv("PURPLEMCP_PURPLE_AI_CONSOLE_VERSION"),
            timeout_seconds=int(os.getenv("PURPLEMCP_PURPLE_AI_TIMEOUT", "30")),
            max_retries=int(os.getenv("PURPLEMCP_PURPLE_AI_MAX_RETRIES", "3"))
        )
    
    def create_config(self) -> PurpleAIConfig:
        """Create PurpleAIConfig from settings."""
        
        from purple_mcp.libs.purple_ai import PurpleAIConsoleDetails
        
        console_details = None
        if self.account_id:
            console_details = PurpleAIConsoleDetails(
                account_id=self.account_id,
                console_version=self.console_version
            )
        
        return PurpleAIConfig(
            graphql_url=self.console_base_url.rstrip("/") + "/web/api/v2.1/graphql",
            auth_token=self.service_token,
            console_details=console_details
        )

# Global settings instance
purple_ai_settings = PurpleAISettings.from_environment()

# Usage
async def production_purple_ai_query(question: str) -> Optional[str]:
    """Production-ready Purple AI query with all best practices."""
    
    config = purple_ai_settings.create_config()
    
    # Use retry logic and error handling
    return await ask_purple_with_retry(
        question, 
        config,
        max_retries=purple_ai_settings.max_retries
    )
```
