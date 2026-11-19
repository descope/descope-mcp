#!/usr/bin/env python3
"""FastMCP integration example with Descope authentication and connection tokens.

This example demonstrates:
1. Protecting MCP tools with Descope session validation and scope validation
2. Getting connection tokens from Descope when required by tools
3. Using connection tokens to call external APIs (Google Calendar)
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

example_dir = Path(__file__).parent
root_dir = example_dir.parent.parent
sdk_src = root_dir / "src"
if sdk_src.exists():
    sys.path.insert(0, str(sdk_src))

from fastmcp import FastMCP
from fastmcp.server.auth.providers.descope import DescopeProvider

from descope_mcp import (
    DescopeMCP,
    InsufficientScopeError,
    get_connection_token,
    validate_token,
    validate_token_require_scopes_and_get_user_id,
)

try:
    import httpx
except ImportError:
    httpx = None


def create_mcp_server():
    """Create a FastMCP server with Descope authentication and Google Calendar integration.

    This example demonstrates:
    - Token validation with scope checking
    - Connection token retrieval using MCP access tokens
    - External API calls with connection tokens
    - Public and protected tools with different scope requirements

    Note: Only one FastMCP server can run per process.
    Each server listens on stdin/stdout for MCP protocol communication.
    """

    # Initialize Descope SDK
    DescopeMCP(
        well_known_url=os.getenv(
            "DESCOPE_MCP_WELL_KNOWN_URL",
            "https://api.descope.com/your-project-id/.well-known/openid-configuration",
        ),
        mcp_server_url=os.getenv("MCP_SERVER_URL", "https://your-mcp-server.com"),
    )

    GOOGLE_CALENDAR_APP_ID = os.getenv("GOOGLE_CALENDAR_APP_ID", "google-calendar")

    # FastMCP auth: configure Descope as the auth layer for your MCP server
    auth_provider = DescopeProvider(
        config_url=os.getenv(
            "DESCOPE_MCP_WELL_KNOWN_URL",
            "https://api.descope.com/your-project-id/.well-known/openid-configuration",
        ),
        base_url=os.getenv("MCP_SERVER_URL", "https://your-mcp-server.com"),
    )
    mcp = FastMCP(name="descope-calendar-server", auth=auth_provider)

    # Public tool - no authentication required
    @mcp.tool()
    def public_info() -> str:
        """Get public information - no authentication required."""
        return "This is public information"

    # Authenticated tool - requires valid token but no specific scopes
    @mcp.tool()
    def authenticated_info(mcp_access_token: str) -> str:
        """Get authenticated user information.

        Requires a valid MCP access token.
        """
        try:
            token_result = validate_token(mcp_access_token)
            user_id = token_result.get("sub") or token_result.get("userId")
            return f"Authenticated user information for user: {user_id}"
        except Exception as e:
            return json.dumps({"error": f"Authentication failed: {str(e)}"})

    # Scope-protected tool - requires 'read' scope
    @mcp.tool()
    def read_data(mcp_access_token: str) -> str:
        """Read data - requires 'read' scope."""
        try:
            # Validate token, require scopes, and get user ID in one call
            user_id = validate_token_require_scopes_and_get_user_id(
                mcp_access_token, required_scopes=["read"]
            )
            return f"Data read successfully for user {user_id}"
        except InsufficientScopeError:
            raise
        except Exception as e:
            return json.dumps({"error": f"Authorization failed: {str(e)}"})

    # Google Calendar tool - requires 'calendar.read' scope and uses connection token
    @mcp.tool()
    async def get_calendar_events(
        mcp_access_token: str, max_results: int = 10, time_min: Optional[str] = None
    ) -> str:
        """Get Google Calendar events for the authenticated user.

        Requires 'calendar.read' scope in the MCP access token.
        Uses Descope connection token to access Google Calendar API.
        """
        try:
            # Validate token, require scopes, and get user ID in one call
            user_id = validate_token_require_scopes_and_get_user_id(
                mcp_access_token, required_scopes=["calendar.read"]
            )

            # Get connection token using MCP access token (enables policy enforcement)
            google_token = get_connection_token(
                user_id=user_id,
                app_id=GOOGLE_CALENDAR_APP_ID,
                scopes=["https://www.googleapis.com/auth/calendar"],
                access_token=mcp_access_token,  # Uses access token by default
            )

            # Call Google Calendar API with connection token
            if not httpx:
                raise ImportError(
                    "httpx required for API calls. Install with: pip install httpx"
                )

            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {google_token}",
                    "Accept": "application/json",
                }

                params = {
                    "maxResults": max_results,
                    "singleEvents": True,
                    "orderBy": "startTime",
                }
                if time_min:
                    params["timeMin"] = time_min

                response = await client.get(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers=headers,
                    params=params,
                    timeout=10.0,
                )
                response.raise_for_status()

                events = response.json()
                formatted_events = []
                for item in events.get("items", [])[:max_results]:
                    formatted_events.append(
                        {
                            "id": item.get("id"),
                            "summary": item.get("summary", "No title"),
                            "start": item.get("start", {}).get("dateTime")
                            or item.get("start", {}).get("date"),
                            "end": item.get("end", {}).get("dateTime")
                            or item.get("end", {}).get("date"),
                            "location": item.get("location"),
                            "description": item.get("description", "")[:100]
                            if item.get("description")
                            else None,
                        }
                    )

                return json.dumps(
                    {
                        "status": "success",
                        "user_id": user_id,
                        "events_count": len(formatted_events),
                        "events": formatted_events,
                    },
                    indent=2,
                )

        except InsufficientScopeError:
            raise
        except httpx.HTTPStatusError as e:
            return json.dumps(
                {
                    "error": f"Google Calendar API error: {e.response.status_code}",
                    "details": e.response.text[:200],
                }
            )
        except Exception as e:
            return json.dumps({"error": str(e), "type": type(e).__name__})

    @mcp.tool()
    async def list_calendars(mcp_access_token: str) -> str:
        """List user's Google Calendars.

        Requires 'calendar.read' scope in the MCP access token.
        """
        user_id = validate_token_require_scopes_and_get_user_id(
            mcp_access_token, required_scopes=["calendar.read"]
        )
        return json.dumps({"message": "Calendar list retrieved", "user_id": user_id})

    return mcp


def main():
    """Create and run the MCP server.

    Note: Only one FastMCP server can run per process.
    Each server listens on stdin/stdout for MCP protocol communication.
    """
    mcp = create_mcp_server()
    mcp.run()


if __name__ == "__main__":
    main()
