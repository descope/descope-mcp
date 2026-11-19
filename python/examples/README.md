# MCP Descope SDK Examples

This directory contains example implementations demonstrating how to use the MCP Descope SDK.

## Available Examples

### 1. FastMCP Calendar (`fastmcp_calendar/`)

Demonstrates protecting MCP tools with Descope authentication and using connection tokens:
- Token validation with audience claim
- Scope-based authorization using `require_scopes()` and `validate_token_require_scopes_and_get_user_id()`
- Connection token retrieval using MCP access tokens
- Google Calendar API integration
- MCP spec-compliant error handling

**Quick Start:**
```bash
cd fastmcp_calendar
uv sync && uv run python fastmcp_example.py
```

### 2. Tenant Token (`tenant_token/`)

Demonstrates fetching tenant tokens using management key:
- Tenant token fetching with management key
- No user session required
- Tenant-level resource access
- Using `DescopeMCP` class for initialization

**Quick Start:**
```bash
cd tenant_token
uv sync && uv run python fetch_tenant_token_example.py
```

## Running Examples

### Using uv (Recommended)

Each example directory has its own `pyproject.toml` file for easy dependency management:

```bash
# Navigate to any example directory
cd examples/fastmcp_calendar  # or tenant_token

# Install dependencies
uv sync

# Run the example
uv run python <example_file>.py
```

### Using pip

```bash
# Navigate to any example directory
cd examples/fastmcp_calendar  # or tenant_token

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install SDK in development mode
cd ../..
pip install -e .
cd examples/<example_name>

# Run the example
python <example_file>.py
```

## Prerequisites

All examples require:
- Python 3.10 or higher
- Descope project configured
- Environment variables set (see each example's README)

## Environment Variables

Common environment variables used across examples:

- `DESCOPE_MCP_WELL_KNOWN_URL`: MCP server well-known URL
- `DESCOPE_MANAGEMENT_KEY`: Descope management API key (optional, needed for token operations)
- `MCP_SERVER_URL`: Your MCP server URL (for audience validation)

See each example's README for specific requirements.

## Getting Help

- Check each example's README for detailed instructions
- See the main [README.md](../README.md) for SDK documentation
- Review example code comments for implementation details
