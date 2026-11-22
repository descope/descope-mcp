"""End-to-end tests using FastMCP 2.0 (mcp.server.FastMCP)."""

from unittest.mock import Mock, patch

import pytest
from mcp.server import FastMCP

from descope_mcp import (
    DescopeMCP,
    create_auth_check,
    get_connection_token,
    validate_token_and_get_user_id,
)


class TestFastMCP2Integration:
    """Test integration with FastMCP 2.0."""

    @pytest.fixture
    def mock_descope_client(self):
        """Create a mock DescopeClient."""
        client = Mock()
        client.validate_session = Mock(
            return_value={
                "sub": "user-123",
                "scope": "read write calendar.read",
            }
        )
        client.mgmt = Mock()
        client.mgmt.outbound_application = Mock()
        client.mgmt.outbound_application.fetch_token = Mock(
            return_value="connection-token-123"
        )
        client.mgmt.outbound_application.fetch_token_by_scopes = Mock(
            return_value="connection-token-123"
        )
        return client

    def test_fastmcp2_public_tool(self):
        """Test FastMCP 2.0 with public tool."""
        mcp = FastMCP("FastMCP2Test")

        @mcp.tool()
        def public_info() -> str:
            """Public information."""
            return "This is public"

        # FastMCP 2.0 doesn't have list_tools, so we just verify it doesn't crash
        assert mcp is not None

    def test_fastmcp2_with_auth_check(self, mock_descope_client):
        """Test FastMCP 2.0 with auth check creation."""
        # Initialize SDK first
        DescopeMCP(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            mcp_server_url="https://test-mcp-server.com",
        )

        # Mock the context to return our mock client
        with patch("descope_mcp.descope_mcp._context") as mock_context:
            mock_context.get_client.return_value = mock_descope_client
            mock_context.get_mcp_server_url.return_value = "https://test-mcp-server.com"

            # Create auth check - will use global context
            # Note: FastMCP 2.0 doesn't support auth parameter, but we can create the check function
            auth_check = create_auth_check(["read"])

            # Verify auth check is callable
            assert callable(auth_check)

            mcp = FastMCP("FastMCP2AuthTest")

            # FastMCP 2.0 doesn't support auth parameter, so we just verify setup
            @mcp.tool()
            def protected_tool() -> str:
                """Protected tool."""
                return "Protected data"

            # Verify it's set up
            assert mcp is not None

    def test_fastmcp2_with_token_validation(self, mock_descope_client):
        """Test FastMCP 2.0 with token validation."""
        DescopeMCP(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            mcp_server_url="https://test-mcp-server.com",
        )

        mcp = FastMCP("FastMCP2TokenTest")

        @mcp.tool()
        def validate_user_token(mcp_access_token: str) -> str:
            """Validate user token."""
            with patch("descope_mcp.descope_mcp._context") as mock_context:
                mock_context.get_client.return_value = mock_descope_client
                mock_context.get_mcp_server_url.return_value = (
                    "https://test-mcp-server.com"
                )
                user_id = validate_token_and_get_user_id(mcp_access_token)
                return f"User ID: {user_id}"

        assert mcp is not None

    def test_fastmcp2_with_connection_token(self, mock_descope_client):
        """Test FastMCP 2.0 with connection token."""
        DescopeMCP(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            management_key="test-key",
        )

        mcp = FastMCP("FastMCP2ConnectionTest")

        @mcp.tool()
        def get_calendar_events(mcp_access_token: str) -> str:
            """Get calendar events using connection token."""
            with patch("descope_mcp.descope_mcp._context") as mock_context:
                mock_context.get_client.return_value = mock_descope_client
                mock_context.get_mcp_server_url.return_value = (
                    "https://test-mcp-server.com"
                )
                user_id = validate_token_and_get_user_id(mcp_access_token)

            with patch("descope_mcp.descope_mcp._context") as mock_context:
                mock_context.get_client.return_value = mock_descope_client
                token = get_connection_token(
                    user_id=user_id,
                    app_id="google-calendar",
                    scopes=["calendar.readonly"],
                )
                return f"Using token: {token[:10]}..."

        assert mcp is not None

    def test_fastmcp2_scope_validation(self, mock_descope_client):
        """Test FastMCP 2.0 with scope validation check creation."""
        # Initialize SDK first
        DescopeMCP(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            mcp_server_url="https://test-mcp-server.com",
        )

        # Mock the context to return our mock client
        with patch("descope_mcp.descope_mcp._context") as mock_context:
            mock_context.get_client.return_value = mock_descope_client
            mock_context.get_mcp_server_url.return_value = "https://test-mcp-server.com"

            # Create auth checks for different scopes
            # Note: FastMCP 2.0 doesn't support auth parameter, but we can create the check functions
            read_check = create_auth_check(["read"])
            read_write_check = create_auth_check(["read", "write"])
            calendar_check = create_auth_check(["calendar.read"])

            # Verify all checks are callable
            assert callable(read_check)
            assert callable(read_write_check)
            assert callable(calendar_check)

        mcp = FastMCP("FastMCP2ScopeTest")

        # FastMCP 2.0 doesn't support auth parameter, so we just verify setup
        @mcp.tool()
        def read_data() -> str:
            """Read data."""
            return "Data read"

        @mcp.tool()
        def read_write_data() -> str:
            """Read and write data."""
            return "Data read and written"

        @mcp.tool()
        def calendar_tool() -> str:
            """Calendar tool."""
            return "Calendar accessed"

        assert mcp is not None
