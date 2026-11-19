"""Connection token functions for Descope MCP SDK.

This module provides functions for retrieving OAuth access tokens for
outbound applications (connections) configured in Descope.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None

from descope import DescopeClient


# Import context lazily to avoid circular dependency
def _get_context():
    from .descope_mcp import _context

    return _context


logger = logging.getLogger(__name__)


def get_connection_token(
    user_id: str,
    app_id: str,
    scopes: Optional[List[str]] = None,
    tenant_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
    descope_client: Optional[DescopeClient] = None,
    project_id: Optional[str] = None,
    management_key: Optional[str] = None,
) -> str:
    """Get connection token from Descope for a user.

    This function retrieves an OAuth access token for a connection/outbound application
    (like Google Calendar, Slack, etc.) that was configured in Descope.

    By default, this function uses the MCP server access token to fetch connection tokens.
    This enables policy enforcement through Descope's Access Control Plane. Management
    keys can be used as a fallback for tenant-level tokens or when access tokens aren't available.

    Authentication methods (in order of preference):
    1. MCP server access token (default, recommended) - enables policy enforcement
    2. DescopeClient instance (uses its configured management key)
    3. project_id and management_key directly (fallback for tenant tokens)

    Args:
        user_id: User ID from the validated MCP server token
        app_id: Connection/outbound application ID configured in Descope
        scopes: Optional scopes to request (if None, uses default scopes)
        tenant_id: Optional tenant ID for tenant-level tokens
        options: Optional additional options (e.g., {"refreshToken": True})
        access_token: MCP server access token (default method, enables policy enforcement)
        descope_client: Optional DescopeClient instance (fallback to management key)
        project_id: Optional project ID (required if using management_key)
        management_key: Optional management key (fallback method, required for tenant tokens)

    Returns:
        Connection access token string

    Raises:
        ValueError: If no authentication method is available
        Exception: If token retrieval fails

    Example:
        ```python
        from descope_mcp import get_connection_token

        # Using MCP server access token (default, recommended)
        google_token = get_connection_token(
            user_id="user-123",
            app_id="google-calendar",
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            access_token="mcp-server-access-token"  # From validated MCP request
        )

        # Using DescopeClient (management key fallback)
        google_token = get_connection_token(
            user_id="user-123",
            app_id="google-calendar",
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            descope_client=client
        )

        # Using project_id and management_key directly (fallback)
        google_token = get_connection_token(
            user_id="user-123",
            app_id="google-calendar",
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            project_id="P123456",
            management_key="your-management-key"
        )
        ```
    """
    try:
        # Extract project_id from well_known_url if needed
        def _extract_project_id(well_known_url: str) -> Optional[str]:
            """Extract project ID from well-known URL."""
            try:
                parsed = urlparse(well_known_url)
                path_parts = [p for p in parsed.path.split("/") if p]
                # Well-known URL format: /{project_id}/.well-known/openid-configuration
                if len(path_parts) > 0:
                    return path_parts[0]
            except Exception:
                pass
            return None

        # Priority 1: Use MCP server access token (default, recommended)
        if access_token:
            if not httpx:
                raise ImportError(
                    "httpx is required for access token authentication. "
                    "Install with: pip install httpx"
                )

            # Get project_id from parameter, context, or extract from well_known_url
            proj_id = project_id
            if not proj_id:
                context = _get_context()
                config = context.get_config()
                if config:
                    proj_id = _extract_project_id(config.well_known_url)

            if not proj_id:
                raise ValueError(
                    "project_id is required when using access_token. "
                    "Either provide project_id parameter or initialize DescopeMCP() with well_known_url "
                    "(project_id will be extracted from the URL)."
                )

            # Make REST API call using access token
            base_url = "https://api.descope.com"
            if scopes:
                url = f"{base_url}/v1/mgmt/outbound/app/user/token"
                payload = {
                    "appId": app_id,
                    "userId": user_id,
                    "scopes": scopes,
                    "options": options or {},
                }
            else:
                url = f"{base_url}/v1/mgmt/outbound/app/user/token/latest"
                payload = {"appId": app_id, "userId": user_id, "options": options or {}}

            if tenant_id:
                payload["tenantId"] = tenant_id

            headers = {
                "Authorization": f"Bearer {proj_id}:{access_token}",
                "Content-Type": "application/json",
            }

            response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            return result["token"]["accessToken"]

        # Priority 2: Use DescopeClient (management key)
        if descope_client:
            client = descope_client
        elif project_id and management_key:
            # Create DescopeClient with provided credentials
            client = DescopeClient(
                project_id=project_id,
                management_key=management_key,
            )
        else:
            # Try to use global context
            context = _get_context()
            client = context.get_client()
            if client is None:
                raise ValueError(
                    "No authentication method provided. "
                    "Provide access_token (recommended), call DescopeMCP() first, "
                    "pass descope_client, or provide project_id and management_key."
                )

        # Fetch token using Descope SDK (management key method)
        if scopes:
            token = client.mgmt.outbound_application.fetch_token_by_scopes(
                app_id=app_id,
                user_id=user_id,
                scopes=scopes,
                options=options or {},
                tenant_id=tenant_id,
            )
        else:
            token = client.mgmt.outbound_application.fetch_token(
                app_id=app_id,
                user_id=user_id,
                tenant_id=tenant_id,
                options=options or {},
            )
        return token
    except Exception as e:
        raise Exception(f"Failed to get connection token: {e}")
