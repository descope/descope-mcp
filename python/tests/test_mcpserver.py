"""End-to-end tests using official Python MCP SDK (Server)."""

from unittest.mock import Mock, patch

import pytest
from mcp.server import Server

from descope_mcp import DescopeMCP, get_connection_token, validate_token_and_get_user_id


class TestMCPServerIntegration:
    """Test integration with official MCP SDK Server."""

    @pytest.fixture
    def mock_descope_client(self):
        """Create a mock DescopeClient."""
        client = Mock()
        client.validate_session = Mock(
            return_value={"sub": "user-123", "scope": "read write"}
        )
        client.mgmt = Mock()
        client.mgmt.outbound_application = Mock()
        client.mgmt.outbound_application.fetch_token = Mock(
            return_value="connection-token-123"
        )
        return client

    def test_server_creation(self):
        """Test basic Server creation."""
        mcp = Server("DescopeTest")
        assert mcp is not None
        assert mcp.name == "DescopeTest"

    def test_server_with_descope_functions(self, mock_descope_client):
        """Test Server with Descope functions."""
        # Initialize SDK
        DescopeMCP(
            well_known_url="https://api.descope.com/test/.well-known/openid-configuration",
            management_key="test-key",
            mcp_server_url="https://test-mcp-server.com",
        )

        # Create MCP server
        mcp = Server("DescopeTest")

        # Verify we can use Descope functions with the server
        with patch("descope_mcp.descope_mcp._context") as mock_context:
            mock_context.get_client.return_value = mock_descope_client
            mock_context.get_mcp_server_url.return_value = "https://test-mcp-server.com"
            user_id = validate_token_and_get_user_id("test-token")
            assert user_id == "user-123"

        assert mcp is not None
