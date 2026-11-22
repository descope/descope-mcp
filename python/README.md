# Descope Python MCP SDK

Python SDK for integrating Descope authentication and authorization with MCP (Model Context Protocol) servers.

## Overview

The Descope Python MCP SDK provides authorization for MCP servers:

- **Token validation** with scope and audience enforcement
- **Connection token retrieval** using MCP server access tokens (default) or management keys
- **Scope validation** following the MCP spec for insufficient scope errors
- **Integration** with FastMCP and the official MCP SDK

## Installation

```bash
pip install descope-mcp
```

## Quick Start

```python
from mcp.server import FastMCP
from descope_mcp import DescopeMCP, validate_token, require_scopes, get_connection_token

# Initialize SDK
DescopeMCP(
    well_known_url="https://api.descope.com/your-project-id/.well-known/openid-configuration",
    mcp_server_url="https://your-mcp-server.com"
)

mcp = FastMCP("my-server")

@mcp.tool()
async def get_calendar_events(mcp_access_token: str) -> str:
    """Get calendar events - requires 'calendar.read' scope."""
    # Validate token and check scopes.
    # InsufficientScopeError is returned to the client as a tool error.
    token_result = validate_token(mcp_access_token)
    require_scopes(token_result, ["calendar.read"])

    # Get user ID and connection token
    user_id = token_result.get("sub") or token_result.get("userId")
    google_token = get_connection_token(
        user_id=user_id,
        app_id="google-calendar",
        scopes=["https://www.googleapis.com/auth/calendar"],
        access_token=mcp_access_token
    )

    # Use token to call external API
    return "Events retrieved"
```

## Set up your Descope MCP Server (and get your `.well-known` URL)

In Descope, create/configure your MCP server in **Agentic Identity Hub → MCP Servers → Settings**. Descope’s docs walk through the settings, including:

- **MCP Server URL**: if set, this becomes the `aud` claim in access tokens (and should match the `mcp_server_url` you pass to this SDK).
- **Discovery endpoints**: use the server’s discovery settings to copy the MCP Server **`.well-known` OpenID configuration URL** you pass as `well_known_url`.

See: [Descope docs — MCP Server Settings](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)

## Token Validation

Validate MCP server access tokens with signature verification, expiration checking, and audience validation:

```python
from descope_mcp import validate_token, validate_token_and_get_user_id

# Get full validation result
result = validate_token(access_token)
user_id = result.get("sub") or result.get("userId")
scopes = result.get("scope", "").split()

# Or get user ID directly
user_id = validate_token_and_get_user_id(access_token)
```

## Scope Validation

The SDK provides scope validation that follows the MCP spec's [Runtime Insufficient Scope Errors](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization#runtime-insufficient-scope-errors).

### Using require_scopes()

```python
from descope_mcp import validate_token, require_scopes

@mcp.tool()
def my_tool(mcp_access_token: str) -> str:
    token_result = validate_token(mcp_access_token)
    require_scopes(token_result, ["read", "write"])
    return "Success"
```

`require_scopes()` reads the token's space-separated `scope` claim. Let `InsufficientScopeError` propagate out of the tool: the MCP server then returns the call as a tool error (`isError: true`). Don't catch it and `return e.to_json()`, because that reports the denial as a successful result.

### InsufficientScopeError

When `require_scopes()` detects missing scopes, it raises an `InsufficientScopeError` that follows the MCP spec (RFC 6750 Section 3.1):

```python
try:
    require_scopes(token_result, ["calendar.read"])
except InsufficientScopeError as e:
    missing = e.missing_scopes  # ["calendar.read"]
    combined = e.combined_scopes  # ["read", "write", "calendar.read"]
    scope_param = e.scope_parameter  # "read write calendar.read"
    
    # Get MCP spec-compliant JSON response
    error_json = e.to_json()
```

The error includes:
- `error`: "insufficient_scope"
- `scope`: Space-separated list of all scopes (existing + required) - uses recommended approach
- `error_description`: Human-readable description
- `missing_scopes`: List of missing scopes
- `token_scopes`: List of scopes in the token
- `required_scopes`: List of required scopes

## Connection Tokens

Retrieve OAuth tokens for third-party services stored in Descope's Connections vault:

```python
from descope_mcp import get_connection_token

# Get token with specific scopes (uses access token by default)
token = get_connection_token(
    user_id="user-123",
    app_id="google-calendar",
    scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    access_token=mcp_access_token  # Enables policy enforcement
)

# Get latest token (any scopes)
token = get_connection_token(
    user_id="user-123",
    app_id="google-calendar",
    access_token=mcp_access_token
)
```

The SDK uses MCP server access tokens by default for policy enforcement. Management keys can be used as a fallback for tenant-level tokens or when access tokens aren't available.

## API Reference

### DescopeMCP Class

```python
from descope_mcp import DescopeMCP

mcp = DescopeMCP(
    well_known_url: str,           # Required: MCP server well-known URL
    management_key: Optional[str], # Optional: Fallback for connection token fetching
    mcp_server_url: Optional[str] # Optional: Audience for token validation
)
```

**Methods:**
- `validate_token(access_token: str) -> TokenValidationResult` - Validates token and returns full result
- `validate_token_and_get_user_id(access_token: str) -> str` - Validates token and returns user ID
- `require_scopes(token_result: TokenValidationResult, required_scopes: List[str]) -> None` - Validates required scopes
- `get_connection_token(user_id: str, app_id: str, scopes: Optional[List[str]] = None, access_token: Optional[str] = None) -> str` - Retrieves connection token

### Standalone Functions

```python
from descope_mcp import (
    validate_token,
    validate_token_and_get_user_id,
    require_scopes,
    InsufficientScopeError,
    get_connection_token,
    init_descope_mcp,
    TokenValidationResult
)

# Initialize global state
init_descope_mcp(
    well_known_url="https://api.descope.com/your-project-id/.well-known/openid-configuration",
    mcp_server_url="https://your-mcp-server.com"
)

# Use functions directly
result = validate_token(access_token)
user_id = validate_token_and_get_user_id(access_token)
require_scopes(result, ["read", "write"])
token = get_connection_token(user_id="user-123", app_id="google-calendar", access_token=access_token)
```

## Examples

See the [examples directory](./examples/) for complete working examples:

- **[FastMCP Calendar](./examples/fastmcp_calendar/)** - Google Calendar integration with scope validation and connection token retrieval
- **[Tenant Tokens](./examples/tenant_token/)** - Fetching tenant-level connection tokens

## Configuration

### Well-Known URL Format

```
https://api.descope.com/{project_id}/.well-known/openid-configuration
```

The SDK automatically extracts the project ID from this URL when needed.

### Environment Variables

```bash
export DESCOPE_MCP_WELL_KNOWN_URL="https://api.descope.com/your-project-id/.well-known/openid-configuration"
export MCP_SERVER_URL="https://your-mcp-server.com"
export DESCOPE_MANAGEMENT_KEY="your-management-key"  # Optional
```

## Security Best Practices

1. **Always provide `mcp_server_url`** for audience validation to prevent token reuse
2. **Use access tokens by default** to enable policy enforcement
3. **Validate tokens on every request** - don't cache validation results
4. **Use `require_scopes()` for scope validation** - ensures MCP spec compliance
5. **Let `InsufficientScopeError` propagate** - the MCP server returns it as a tool error

## Compatibility

- **Python**: 3.10+
- **MCP SDK**: 1.x (`mcp>=1.0.0,<2`)
- **Descope SDK**: 1.0.0+

The SDK can be imported alongside the official Descope Python SDK without conflicts.

## License

MIT

## Support

- [Documentation](https://docs.descope.com)
- [GitHub Issues](https://github.com/your-org/mcp-descope/issues)
- [Community Slack](https://www.descope.com/community)
