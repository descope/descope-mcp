"""DescopeMCP SDK client and initialization for Descope MCP integration.

This module provides the main DescopeMCP client class and SDK functionality including:
- DescopeMCP class (similar to DescopeClient in Descope SDK)
- Global context and initialization
- DescopeClient creation and configuration
- FastMCP integration helpers
- Utility functions for headers and SDK configuration
"""

import logging
import platform
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

try:
    from importlib.metadata import version as _get_version  # type: ignore[no-redef]
except ImportError:  # pragma: no cover
    try:
        from importlib_metadata import version as _get_version  # type: ignore[no-redef]
    except ImportError:
        # isort: off
        from pkg_resources import get_distribution as _get_version  # type: ignore[no-redef]
        # isort: on

# Import DescopeClient lazily for runtime compatibility in restricted environments.
# (Some environments may block requests/SSL initialization at import time.)
if TYPE_CHECKING:  # pragma: no cover
    from descope import DescopeClient
else:  # pragma: no cover
    DescopeClient = Any  # type: ignore
from mcp.server import FastMCP

from . import __version__
from .connections import get_connection_token as _get_connection_token
from .session import (
    TokenValidationResult,
)
from .session import fetch_userinfo as _fetch_userinfo
from .session import require_scopes as _require_scopes
from .session import validate_token as _validate_token
from .session import validate_token_and_get_user_id as _validate_token_and_get_user_id
from .session import (
    validate_token_require_scopes_and_get_user_id as _validate_token_require_scopes_and_get_user_id,
)
from .types import DescopeConfig, ErrorResponse, TokenResponse

logger = logging.getLogger(__name__)


def _get_sdk_version() -> str:
    """Get the version of this SDK."""
    try:
        # First try to get from package metadata
        return _get_version("descope-mcp")  # type: ignore
    except Exception:
        try:
            # Fallback to package's __version__
            return __version__
        except Exception:
            return "unknown"


def _get_default_headers() -> Dict[str, str]:
    """Get default headers for MCP Descope SDK requests (internal use only).

    These headers identify the SDK making the request for Descope's internal tracking.
    The DescopeClient automatically includes these headers in all requests it makes.

    Note: This function is for internal SDK use only. Users should not need to
    manually add these headers - they are automatically included by DescopeClient.

    The DescopeClient already includes headers like:
    - x-descope-sdk-name: python
    - x-descope-sdk-version: <descope-sdk-version>
    - x-descope-sdk-python-version: <python-version>
    - x-descope-project-id: <project-id>
    - Authorization: Bearer <project-id>:<management-key>

    Returns:
        Dictionary of default headers (for internal SDK use only)
    """
    return {
        "Content-Type": "application/json",
        "x-descope-sdk-name": "mcp-python",
        "x-descope-sdk-python-version": platform.python_version(),
        "x-descope-sdk-version": _get_sdk_version(),
    }


def _extract_project_id_from_url(url: str) -> Optional[str]:
    """Extract project ID from well-known URL.

    Args:
        url: Well-known URL (e.g., https://api.descope.com/P123456/.well-known/openid-configuration)

    Returns:
        Project ID or None if not found
    """
    try:
        parsed_url = urlparse(url)
        path_parts = [p for p in parsed_url.path.split("/") if p]
        # Project ID is typically the first part after the domain
        # Format: /P123456/.well-known/openid-configuration
        for part in path_parts:
            if part.startswith("P") and len(part) > 1:
                return part
        return None
    except Exception:
        return None


# Global context for SDK initialization
class _DescopeContext:
    """Global context for Descope SDK configuration."""

    def __init__(self):
        self.config: Optional[DescopeConfig] = None
        self.client: Optional[DescopeClient] = None
        self.mcp_server_url: Optional[str] = (
            None  # MCP server URL for audience validation
        )

    def initialize(
        self,
        well_known_url: str,
        management_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
    ):
        """Initialize the global Descope context.

        Args:
            well_known_url: MCP server well-known URL
            management_key: Optional management key for token operations
            mcp_server_url: Optional MCP server URL to use as audience claim (defaults to well_known_url)
        """
        self.config = DescopeConfig(
            well_known_url=well_known_url, management_key=management_key
        )
        # Use mcp_server_url if provided, otherwise use well_known_url as audience
        self.mcp_server_url = mcp_server_url or well_known_url
        self.client = _get_descope_client(self.config, self.mcp_server_url)

    def get_client(self) -> Optional[DescopeClient]:
        """Get the configured DescopeClient."""
        return self.client

    def get_config(self) -> Optional[DescopeConfig]:
        """Get the configured DescopeConfig."""
        return self.config

    def get_mcp_server_url(self) -> Optional[str]:
        """Get the MCP server URL for audience validation."""
        return self.mcp_server_url

    def reset(self):
        """Reset the global context."""
        self.config = None
        self.client = None
        self.mcp_server_url = None


# Global context instance
_context = _DescopeContext()


class DescopeMCP:
    """Descope MCP SDK client, similar to DescopeClient in the Descope Python SDK.

    This class provides a class-based API for the Descope MCP SDK, allowing you to
    instantiate a client and use it explicitly rather than relying on global state.

    Example:
        ```python
        from descope_mcp import DescopeMCP

        # Create a client instance
        mcp = DescopeMCP(
            well_known_url="https://api.descope.com/your-project-id/.well-known/openid-configuration",
            management_key="your-management-key",
            mcp_server_url="https://your-mcp-server.com"
        )

        # Use the client methods
        user_id = mcp.validate_token_and_get_user_id(access_token)
        token = mcp.get_connection_token(user_id="user-123", app_id="google-calendar")
        ```

    You can also use the global initialization function for convenience:
        ```python
        from descope_mcp import DescopeMCP as init_descope_mcp

        # Initialize global state
        init_descope_mcp(...)

        # Then use standalone functions
        from descope_mcp import validate_token_and_get_user_id, get_connection_token
        ```
    """

    def __init__(
        self,
        well_known_url: str,
        management_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
    ):
        """Initialize the Descope MCP client.

        Args:
            well_known_url: MCP server well-known URL (e.g., https://api.descope.com/your-project-id/.well-known/openid-configuration)
            management_key: Optional management key for token operations (fallback for tenant tokens or when access tokens aren't available).
                           By default, connection tokens are fetched using MCP server access tokens, which enables policy enforcement.
            mcp_server_url: MCP server URL to use as audience claim for token validation.
                           This should be the public URL of your MCP server.
                           If not provided, audience validation is skipped unless an
                           explicit audience is passed to validate methods.
        """
        self.config = DescopeConfig(
            well_known_url=well_known_url, management_key=management_key
        )
        self.mcp_server_url = mcp_server_url
        self._client = _get_descope_client(self.config, self.mcp_server_url)

    @property
    def descope_client(self) -> Optional[DescopeClient]:
        """Get the underlying DescopeClient instance."""
        return self._client

    def validate_token(
        self, access_token: str, audience: Optional[str] = None
    ) -> "TokenValidationResult":
        """Validate token and return full validation result.

        Args:
            access_token: MCP server access token
            audience: Optional audience claim (defaults to mcp_server_url if set)

        Returns:
            TokenValidationResult dictionary with user ID, tenant info, scopes, etc.
            See :class:`TokenValidationResult` for available fields.
        """
        return _validate_token(
            access_token=access_token,
            descope_client=self._client,
            audience=audience if audience is not None else self.mcp_server_url,
        )

    def validate_token_and_get_user_id(
        self, access_token: str, audience: Optional[str] = None
    ) -> str:
        """Validate token and get user ID (convenience method).

        Args:
            access_token: MCP server access token from the request
            audience: Optional audience claim to validate (uses instance's mcp_server_url if set)

        Returns:
            User ID extracted from the validated token

        Raises:
            ValueError: If token is invalid or user ID not found
            Exception: If token validation fails
        """
        return _validate_token_and_get_user_id(
            access_token=access_token,
            descope_client=self._client,
            audience=audience if audience is not None else self.mcp_server_url,
        )

    def validate_token_require_scopes_and_get_user_id(
        self,
        access_token: str,
        required_scopes: List[str],
        audience: Optional[str] = None,
        error_description: Optional[str] = None,
    ) -> str:
        """Validate token, require scopes, and get user ID in one call.

        Convenience method that combines token validation, scope checking,
        and user ID extraction.

        Args:
            access_token: MCP server access token
            required_scopes: List of scopes required for the operation
            audience: Optional audience claim (defaults to mcp_server_url if set)
            error_description: Optional custom error description

        Returns:
            User ID extracted from the validated token

        Raises:
            InsufficientScopeError: If token lacks any required scopes
            ValueError: If token is invalid or user ID not found
        """
        return _validate_token_require_scopes_and_get_user_id(
            access_token=access_token,
            required_scopes=required_scopes,
            descope_client=self._client,
            audience=audience if audience is not None else self.mcp_server_url,
            error_description=error_description,
        )

    def require_scopes(
        self,
        token_result: TokenValidationResult,
        required_scopes: List[str],
        error_description: Optional[str] = None,
    ) -> None:
        """Validate that token has required scopes, raise InsufficientScopeError if not.

        This is a convenience method that wraps the standalone require_scopes function.

        Args:
            token_result: Token validation result from validate_token()
            required_scopes: List of scopes required for the operation
            error_description: Optional custom error description

        Raises:
            InsufficientScopeError: If token lacks any required scopes
        """
        _require_scopes(token_result, required_scopes, error_description)

    def get_connection_token(
        self,
        user_id: str,
        app_id: str,
        scopes: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None,
    ) -> str:
        """Get connection token from Descope for a user.

        By default, uses the provided MCP server access token to fetch connection tokens,
        enabling policy enforcement through Descope's Access Control Plane. Falls back
        to management key if no access token is provided.

        Args:
            user_id: User ID from the validated MCP server token
            app_id: Connection/outbound application ID configured in Descope
            scopes: Optional scopes to request (if None, uses default scopes)
            tenant_id: Optional tenant ID for tenant-level tokens
            options: Optional additional options (e.g., {"refreshToken": True})
            access_token: MCP server access token (recommended, enables policy enforcement)

        Returns:
            Connection access token string

        Raises:
            ValueError: If client not available
            Exception: If token retrieval fails
        """
        return _get_connection_token(
            user_id=user_id,
            app_id=app_id,
            scopes=scopes,
            tenant_id=tenant_id,
            options=options,
            access_token=access_token,
            descope_client=self._client if not access_token else None,
        )

    def fetch_userinfo(
        self,
        access_token: str,
        *,
        project_id: Optional[str] = None,
        userinfo_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Call Descope ``/v1/apps/{project_id}/userinfo`` with the given access token.

        Uses this instance's ``well_known_url`` for API host and project ID unless
        ``userinfo_url`` or ``project_id`` overrides apply. See
        :func:`~descope_mcp.session.fetch_userinfo`.
        """
        return _fetch_userinfo(
            access_token,
            well_known_url=self.config.well_known_url,
            project_id=project_id,
            userinfo_url=userinfo_url,
            timeout=timeout,
        )

    def create_auth_check(
        self, required_scopes: Optional[List[str]] = None
    ) -> Callable:
        """Create an auth check function for FastMCP.

        Args:
            required_scopes: List of required scopes (empty list means auth only, no scope check)

        Returns:
            Auth check function that can be used with FastMCP decorators
        """
        return create_auth_check(
            required_scopes=required_scopes, descope_client=self._client
        )


def init_descope_mcp(
    well_known_url: str,
    management_key: Optional[str] = None,
    mcp_server_url: Optional[str] = None,
) -> None:
    """Initialize the Descope MCP SDK with global configuration (convenience function).

    This is a convenience function that initializes global state. For a class-based
    API similar to DescopeClient, use the DescopeMCP class instead.

    Call this once at the top of your code, and all SDK functions will use
    this configuration automatically. The MCP server URL will be used as the
    audience claim when validating tokens to ensure tokens are only accepted
    if they were issued for this specific MCP server.

    Args:
        well_known_url: MCP server well-known URL (e.g., https://api.descope.com/your-project-id/.well-known/openid-configuration)
        management_key: Optional management key for token operations (required for token validation and connection tokens)
        mcp_server_url: MCP server URL to use as audience claim for token validation.
                       This should be the public URL of your MCP server.
                       If not provided, defaults to well_known_url.
                       This URL will be validated against the 'aud' claim in tokens.

    Example:
        ```python
        from descope_mcp import init_descope_mcp, get_connection_token

        # Initialize once at the top
        # IMPORTANT: Provide your MCP server URL for audience validation
        init_descope_mcp(
            well_known_url="https://api.descope.com/your-project-id/.well-known/openid-configuration",
            management_key="your-management-key",  # Required for token validation
            mcp_server_url="https://your-mcp-server.com"  # Required: Used as audience claim
        )

        # Now all functions work without passing config/client
        token = get_connection_token(
            user_id="user-123",
            app_id="google-calendar"
        )
        ```

    Note:
        The MCP server URL is critical for security. It ensures that tokens
        issued for other applications cannot be used with your MCP server.
        Always provide a specific MCP server URL, not a generic well-known URL.

        For a class-based API (recommended), use the DescopeMCP class:
        ```python
        from descope_mcp import DescopeMCP

        mcp = DescopeMCP(...)
        mcp.validate_token_and_get_user_id(...)
        ```
    """
    _context.initialize(well_known_url, management_key, mcp_server_url)


def _get_descope_client(
    config: DescopeConfig, mcp_server_url: Optional[str] = None
) -> Optional[DescopeClient]:
    """Get or create a DescopeClient from config.

    Args:
        config: Descope configuration
        mcp_server_url: Optional MCP server URL (stored for audience validation)

    Returns:
        DescopeClient instance or None if management_key not provided

    Note:
        The DescopeClient is initialized with project_id and management_key.
        The mcp_server_url is stored separately in the context and used as the
        audience claim when calling validate_session() to ensure tokens are
        only accepted if they were issued for this specific MCP server.

        The DescopeClient automatically includes proper headers:
        - x-descope-sdk-name: python
        - x-descope-sdk-version: <descope-sdk-version>
        - x-descope-sdk-python-version: <python-version>
        - x-descope-project-id: <project-id>
        - Authorization: Bearer <project-id>:<management-key>
    """
    if not config.management_key:
        return None

    # Try to extract project_id from well_known_url
    project_id = _extract_project_id_from_url(config.well_known_url)

    if project_id:
        # Initialize DescopeClient with project_id and management_key
        # Note: The MCP server URL (audience) is not passed to DescopeClient initialization,
        # but is stored in the context and used when calling validate_session()
        return DescopeClient(
            project_id=project_id,
            management_key=config.management_key,
        )
    return None


# Session validation and connection token functions are now in separate modules:
# - session.py: validate_token_and_get_user_id()
# - connections.py: get_connection_token()
# These are imported at the top of this file for backward compatibility.


def get_descope_client(config: DescopeConfig) -> DescopeClient:
    """Get DescopeClient from config, raising error if not available.

    Args:
        config: Descope configuration

    Returns:
        DescopeClient instance

    Raises:
        ValueError: If management_key is not provided

    Example:
        ```python
        from descope_mcp import DescopeConfig, get_descope_client

        config = DescopeConfig(well_known_url="...", management_key="...")
        client = get_descope_client(config)
        ```
    """
    client = _get_descope_client(config)
    if not client:
        raise ValueError(
            "Descope management_key is required. "
            "Provide it in DescopeConfig to use token validation and outbound app tokens."
        )
    return client


def create_auth_check(
    required_scopes: Optional[List[str]] = None,
    descope_client: Optional[DescopeClient] = None,
) -> Callable:
    """Create an auth check function for FastMCP 3.0+ that validates Descope token and scopes.

    **Note:** This function is designed for FastMCP 3.0+ which supports the `auth` parameter
    in the `@mcp.tool()` decorator. For FastMCP 2.0, validate tokens manually in your tool functions.

    This function creates an auth check that can be used with FastMCP 3.0+'s @mcp.tool(auth=...)
    decorator. It validates the MCP server access token and checks for required scopes.

    Args:
        required_scopes: List of required scopes (empty list means auth only, no scope check)
        descope_client: Optional Descope client instance (uses global context if not provided)

    Returns:
        Auth check function that can be used with FastMCP decorators

    Example:
        ```python
        from descope_mcp import DescopeMCP, create_auth_check

        # Initialize once
        DescopeMCP(well_known_url="...", management_key="...")

        # Require authentication only
        @mcp.tool(auth=create_auth_check([]))
        def authenticated_tool():
            return "Authenticated"

        # Require specific scopes
        @mcp.tool(auth=create_auth_check(["read", "write"]))
        def read_write_tool():
            return "Read/write access"
        ```
    """
    # Use provided client or global context
    if descope_client is None:
        descope_client = _context.get_client()
        if descope_client is None:
            raise ValueError(
                "No Descope client available. "
                "Either call DescopeMCP() first or pass descope_client parameter."
            )

    required_scopes = required_scopes or []

    def check(ctx) -> bool:
        """Check if request has valid token and required scopes."""
        # Get access token from context
        # In FastMCP v3.0.0, this would come from ctx.token
        token = getattr(ctx, "token", None)

        if not token:
            return False

        # Extract token string if it's an object
        token_str = token.token if hasattr(token, "token") else str(token)

        try:
            # Get audience from context if available
            audience = _context.get_mcp_server_url() if descope_client is None else None

            # Validate token and get user ID (uses closure's descope_client)
            # Audience validation ensures token is intended for this MCP server
            # Import here to avoid circular dependency
            from .session import validate_token_and_get_user_id

            user_id = validate_token_and_get_user_id(
                token_str, descope_client, audience=audience
            )

            # If no scopes required, just check authentication
            if not required_scopes:
                return True

            # Check if token has required scopes
            token_scopes = getattr(token, "scopes", [])
            if isinstance(token_scopes, str):
                token_scopes = token_scopes.split()

            # Verify all required scopes are present
            required_set = set(required_scopes)
            token_set = set(token_scopes)

            return required_set.issubset(token_set)
        except Exception as e:
            logger.error(f"Auth check failed: {e}")
            return False

    return check


def add_descope_tools(mcp: FastMCP, config: DescopeConfig) -> None:
    """Add Descope tools to an existing FastMCP server.

    This function registers all Descope authentication tools with a FastMCP instance.
    You can also use the individual functions directly with FastMCP decorators.

    Args:
        mcp: FastMCP server instance to extend
        config: Descope configuration

    Example:
        ```python
        from mcp.server import FastMCP
        from descope_mcp import add_descope_tools, DescopeConfig

        # Create your FastMCP server
        mcp = FastMCP("my-server")

        # Add Descope tools
        config = DescopeConfig(
            well_known_url="https://api.descope.com/your-project-id/mcp",
            management_key="your-management-key"  # Optional
        )
        add_descope_tools(mcp, config)

        # Add your own tools
        @mcp.tool()
        def my_custom_tool():
            return "Hello"

        # Run the server
        mcp.run()
        ```

    Alternatively, use the functions directly:
        ```python
        from mcp.server import FastMCP
        from descope_mcp.descope_mcp import fetch_user_token, DescopeConfig

        mcp = FastMCP("my-server")
        config = DescopeConfig(well_known_url="...", management_key="...")

        @mcp.tool()
        async def fetch_user_token_tool(app_id: str, user_id: str, ...):
            return await fetch_user_token(config, app_id, user_id, ...)
        ```
    """
    descope_client = _get_descope_client(config)

    @mcp.tool()
    async def fetch_user_token_by_scopes(
        app_id: str,
        user_id: str,
        scopes: List[str],
        options: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> str:
        """Fetch user token with specific scopes."""
        return await _fetch_user_token_by_scopes_impl(
            descope_client, config, app_id, user_id, scopes, options, tenant_id
        )

    @mcp.tool()
    async def fetch_user_token(
        app_id: str,
        user_id: str,
        tenant_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Fetch latest user token."""
        return await _fetch_user_token_impl(
            descope_client, config, app_id, user_id, tenant_id, options
        )

    @mcp.tool()
    async def fetch_tenant_token_by_scopes(
        app_id: str,
        tenant_id: str,
        scopes: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Fetch tenant token with specific scopes."""
        return await _fetch_tenant_token_by_scopes_impl(
            descope_client, config, app_id, tenant_id, scopes, options
        )

    @mcp.tool()
    async def fetch_tenant_token(
        app_id: str,
        tenant_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Fetch latest tenant token."""
        return await _fetch_tenant_token_impl(
            descope_client, config, app_id, tenant_id, options
        )


# Standalone functions that can be used directly with FastMCP decorators
async def fetch_user_token_by_scopes(
    config: DescopeConfig,
    app_id: str,
    user_id: str,
    scopes: List[str],
    options: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """Fetch user token with specific scopes. Use this directly with FastMCP.

    Example:
        @mcp.tool()
        async def get_token(app_id: str, user_id: str, scopes: List[str]):
            return await fetch_user_token_by_scopes(config, app_id, user_id, scopes)
    """
    descope_client = _get_descope_client(config)
    return await _fetch_user_token_by_scopes_impl(
        descope_client, config, app_id, user_id, scopes, options, tenant_id
    )


async def fetch_user_token(
    config: DescopeConfig,
    app_id: str,
    user_id: str,
    tenant_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """Fetch latest user token. Use this directly with FastMCP."""
    descope_client = _get_descope_client(config)
    return await _fetch_user_token_impl(
        descope_client, config, app_id, user_id, tenant_id, options
    )


async def fetch_tenant_token_by_scopes(
    config: DescopeConfig,
    app_id: str,
    tenant_id: str,
    scopes: List[str],
    options: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
) -> str:
    """Fetch tenant token with specific scopes. Use this directly with FastMCP."""
    descope_client = _get_descope_client(config)
    return await _fetch_tenant_token_by_scopes_impl(
        descope_client, config, app_id, tenant_id, scopes, options, access_token
    )


async def fetch_tenant_token(
    config: DescopeConfig,
    app_id: str,
    tenant_id: str,
    options: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
) -> str:
    """Fetch latest tenant token. Use this directly with FastMCP."""
    descope_client = _get_descope_client(config)
    return await _fetch_tenant_token_impl(
        descope_client, config, app_id, tenant_id, options, access_token
    )


# Implementation functions
async def _fetch_user_token_by_scopes_impl(
    descope_client: Optional[DescopeClient],
    config: DescopeConfig,
    app_id: str,
    user_id: str,
    scopes: List[str],
    options: Optional[Dict[str, Any]],
    tenant_id: Optional[str],
) -> str:
    """Implementation of fetch_user_token_by_scopes."""
    try:
        if descope_client:
            token = descope_client.mgmt.outbound_application.fetch_token_by_scopes(
                app_id, user_id, scopes, options or {}, tenant_id
            )
        else:
            raise NotImplementedError(
                "Connecting to remote MCP server not yet implemented. "
                "Please provide management_key for direct API access."
            )
        response = TokenResponse(token=token)
        return response.model_dump_json()
    except Exception as e:
        logger.error(f"Error fetching user token by scopes: {e}")
        error_response = ErrorResponse(error=str(e))
        return error_response.model_dump_json()


async def _fetch_user_token_impl(
    descope_client: Optional[DescopeClient],
    config: DescopeConfig,
    app_id: str,
    user_id: str,
    tenant_id: Optional[str],
    options: Optional[Dict[str, Any]],
) -> str:
    """Implementation of fetch_user_token."""
    try:
        if descope_client:
            token = descope_client.mgmt.outbound_application.fetch_token(
                app_id, user_id, tenant_id, options or {}
            )
        else:
            raise NotImplementedError(
                "Connecting to remote MCP server not yet implemented. "
                "Please provide management_key for direct API access."
            )
        response = TokenResponse(token=token)
        return response.model_dump_json()
    except Exception as e:
        logger.error(f"Error fetching user token: {e}")
        error_response = ErrorResponse(error=str(e))
        return error_response.model_dump_json()


async def _fetch_tenant_token_by_scopes_impl(
    descope_client: Optional[DescopeClient],
    config: DescopeConfig,
    app_id: str,
    tenant_id: str,
    scopes: List[str],
    options: Optional[Dict[str, Any]],
    access_token: Optional[str] = None,
) -> str:
    """Implementation of fetch_tenant_token_by_scopes."""
    try:
        # If an MCP access token is provided, use REST API so we can authenticate with
        # `Authorization: Bearer <PROJECT_ID:ACCESS_TOKEN>` (policy-enforced).
        if access_token:
            if not httpx:
                raise ImportError(
                    "httpx is required for access token authentication. Install with: pip install httpx"
                )

            project_id = _extract_project_id(config.well_known_url)
            if not project_id:
                raise ValueError(
                    "Could not extract project_id from well_known_url. "
                    "Expected format: https://api.descope.com/{project_id}/.well-known/openid-configuration"
                )

            url = "https://api.descope.com/v1/mgmt/outbound/app/tenant/token"
            payload: Dict[str, Any] = {
                "appId": app_id,
                "tenantId": tenant_id,
                "scopes": scopes,
                "options": options or {},
            }
            headers = {
                "Authorization": f"Bearer {project_id}:{access_token}",
                "Content-Type": "application/json",
            }
            resp = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            token = data["token"]["accessToken"]
            return TokenResponse(token=token).model_dump_json()

        if descope_client:
            token = (
                descope_client.mgmt.outbound_application.fetch_tenant_token_by_scopes(
                    app_id, tenant_id, scopes, options or {}
                )
            )
        else:
            raise NotImplementedError(
                "Connecting to remote MCP server not yet implemented. "
                "Please provide management_key for direct API access."
            )
        response = TokenResponse(token=token)
        return response.model_dump_json()
    except Exception as e:
        logger.error(f"Error fetching tenant token by scopes: {e}")
        error_response = ErrorResponse(error=str(e))
        return error_response.model_dump_json()


async def _fetch_tenant_token_impl(
    descope_client: Optional[DescopeClient],
    config: DescopeConfig,
    app_id: str,
    tenant_id: str,
    options: Optional[Dict[str, Any]],
    access_token: Optional[str] = None,
) -> str:
    """Implementation of fetch_tenant_token."""
    try:
        # If an MCP access token is provided, use the dedicated "latest" endpoint:
        # POST /v1/mgmt/outbound/app/tenant/token/latest
        # with `Authorization: Bearer <PROJECT_ID:ACCESS_TOKEN>` (or management key).
        if access_token:
            if not httpx:
                raise ImportError(
                    "httpx is required for access token authentication. Install with: pip install httpx"
                )

            project_id = _extract_project_id(config.well_known_url)
            if not project_id:
                raise ValueError(
                    "Could not extract project_id from well_known_url. "
                    "Expected format: https://api.descope.com/{project_id}/.well-known/openid-configuration"
                )

            url = "https://api.descope.com/v1/mgmt/outbound/app/tenant/token/latest"
            payload: Dict[str, Any] = {
                "appId": app_id,
                "tenantId": tenant_id,
                "options": options or {},
            }
            headers = {
                "Authorization": f"Bearer {project_id}:{access_token}",
                "Content-Type": "application/json",
            }
            resp = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            token = data["token"]["accessToken"]
            return TokenResponse(token=token).model_dump_json()

        if descope_client:
            token = descope_client.mgmt.outbound_application.fetch_tenant_token(
                app_id, tenant_id, options or {}
            )
        else:
            raise NotImplementedError(
                "Connecting to remote MCP server not yet implemented. "
                "Please provide management_key for direct API access."
            )
        response = TokenResponse(token=token)
        return response.model_dump_json()
    except Exception as e:
        logger.error(f"Error fetching tenant token: {e}")
        error_response = ErrorResponse(error=str(e))
        return error_response.model_dump_json()


def _extract_project_id(well_known_url: str) -> Optional[str]:
    """Extract project ID from well-known URL.

    Expected well-known URL format:
      https://api.descope.com/{project_id}/.well-known/openid-configuration
    """
    try:
        parsed = urlparse(well_known_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[0]
    except Exception:
        return None
    return None


def create_descope_fastmcp_server(
    name: str = "descope",
    config: Optional[DescopeConfig] = None,
    **fastmcp_kwargs: Any,
) -> FastMCP:
    """Create a FastMCP server with Descope tools pre-configured.

    Args:
        name: Server name
        config: Descope configuration (if None, will load from environment)
        **fastmcp_kwargs: Additional arguments to pass to FastMCP constructor

    Returns:
        Configured FastMCP server with Descope tools

    Example:
        ```python
        from descope_mcp import create_descope_fastmcp_server, DescopeConfig

        # Create server with config
        config = DescopeConfig(
            well_known_url="https://api.descope.com/your-project-id/mcp",
            management_key="your-management-key"  # Optional
        )
        mcp = create_descope_fastmcp_server("my-server", config=config)

        # Add your own tools
        @mcp.tool()
        def my_tool():
            return "Hello"

        # Run
        mcp.run()
        ```
    """
    import os

    if config is None:
        well_known_url = os.getenv("DESCOPE_MCP_WELL_KNOWN_URL", "")
        management_key = os.getenv("DESCOPE_MANAGEMENT_KEY", "")

        if not well_known_url:
            raise ValueError(
                "DESCOPE_MCP_WELL_KNOWN_URL environment variable is required"
            )

        config = DescopeConfig(
            well_known_url=well_known_url,
            management_key=management_key if management_key else None,
        )

    mcp = FastMCP(name, **fastmcp_kwargs)
    add_descope_tools(mcp, config)
    return mcp
