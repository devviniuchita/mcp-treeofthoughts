"""Comprehensive tests for FastMCP Cloud authentication.

This test suite validates ensure_cloud_auth_token() function and related
cloud authentication mechanisms, covering the 15% gap identified in test coverage.
"""

import os

from unittest.mock import patch

import jwt
import pytest


class TestCloudAuthenticationDetection:
    """Test FASTMCP_CLOUD environment detection."""

    @patch.dict(os.environ, {"FASTMCP_CLOUD": "true"}, clear=False)
    def test_fastmcp_cloud_true_detection(self):
        """Verify FASTMCP_CLOUD=true is correctly detected."""
        from server import ensure_cloud_auth_token

        # Clear any existing AUTH_TOKEN to test generation
        if "AUTH_TOKEN" in os.environ:
            del os.environ["AUTH_TOKEN"]
        if "FASTMCP_SERVER_AUTH" in os.environ:
            del os.environ["FASTMCP_SERVER_AUTH"]

        # Call function
        ensure_cloud_auth_token()

        # Verify AUTH_TOKEN was generated
        assert "AUTH_TOKEN" in os.environ
        assert os.environ["AUTH_TOKEN"] != ""

    @patch.dict(os.environ, {"FASTMCP_CLOUD": "false"}, clear=False)
    def test_fastmcp_cloud_false_skips_generation(self):
        """Verify FASTMCP_CLOUD=false skips AUTH_TOKEN generation."""
        # Clear AUTH_TOKEN
        if "AUTH_TOKEN" in os.environ:
            del os.environ["AUTH_TOKEN"]

        from server import ensure_cloud_auth_token

        # Call function
        ensure_cloud_auth_token()

        # Verify AUTH_TOKEN was NOT generated (function should skip)
        # Note: This depends on implementation - if FASTMCP_CLOUD=false,
        # the function should not generate a token
        assert "AUTH_TOKEN" not in os.environ or os.environ.get("AUTH_TOKEN") == ""

    @patch.dict(os.environ, {}, clear=True)
    def test_fastmcp_cloud_missing_defaults_false(self):
        """Verify missing FASTMCP_CLOUD defaults to false behavior."""
        from server import ensure_cloud_auth_token

        # Clear AUTH_TOKEN
        if "AUTH_TOKEN" in os.environ:
            del os.environ["AUTH_TOKEN"]

        # Call function
        ensure_cloud_auth_token()

        # Without FASTMCP_CLOUD set, should not generate token
        assert "AUTH_TOKEN" not in os.environ or os.environ.get("AUTH_TOKEN") == ""


class TestAuthTokenGeneration:
    """Test AUTH_TOKEN auto-generation logic."""

    @patch.dict(
        os.environ,
        {"FASTMCP_CLOUD": "true"},
        clear=False,
    )
    def test_auth_token_generated_when_missing(self):
        """Verify AUTH_TOKEN is generated when missing in cloud mode."""
        # Clear existing tokens
        for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
            if key in os.environ:
                del os.environ[key]

        from server import ensure_cloud_auth_token

        # Call function
        ensure_cloud_auth_token()

        # Verify token generated
        assert "AUTH_TOKEN" in os.environ
        token = os.environ["AUTH_TOKEN"]
        assert len(token) > 100  # JWT tokens are long

    @patch.dict(
        os.environ,
        {"FASTMCP_CLOUD": "true", "AUTH_TOKEN": "existing-token-12345"},
        clear=False,
    )
    def test_auth_token_preserved_when_exists(self):
        """Verify existing AUTH_TOKEN is not overwritten."""
        from server import ensure_cloud_auth_token

        original_token = os.environ["AUTH_TOKEN"]

        # Call function
        ensure_cloud_auth_token()

        # Verify token NOT changed
        assert os.environ["AUTH_TOKEN"] == original_token

    @patch.dict(
        os.environ,
        {"FASTMCP_CLOUD": "true", "FASTMCP_SERVER_AUTH": "server-auth-token"},
        clear=False,
    )
    def test_fastmcp_server_auth_respected(self):
        """Verify FASTMCP_SERVER_AUTH prevents AUTH_TOKEN generation."""
        # Clear AUTH_TOKEN
        if "AUTH_TOKEN" in os.environ:
            del os.environ["AUTH_TOKEN"]

        from server import ensure_cloud_auth_token

        # Call function
        ensure_cloud_auth_token()

        # Verify AUTH_TOKEN not generated (FASTMCP_SERVER_AUTH takes precedence)
        assert "AUTH_TOKEN" not in os.environ or os.environ.get("AUTH_TOKEN") == ""


class TestJWTManagerIntegration:
    """Test integration with jwt_manager.get_or_create_token()."""

    @patch.dict(
        os.environ,
        {"FASTMCP_CLOUD": "true"},
        clear=False,
    )
    @patch("server.jwt_manager")
    def test_jwt_manager_called_in_cloud_mode(self, mock_jwt_manager):
        """Verify jwt_manager.get_or_create_token() is called in cloud mode."""
        # Setup mock
        mock_jwt_manager.get_or_create_token.return_value = "mock-jwt-token-rs256"

        # Clear tokens
        for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
            if key in os.environ:
                del os.environ[key]

        from server import ensure_cloud_auth_token

        # Call function
        ensure_cloud_auth_token()

        # Verify jwt_manager was called
        mock_jwt_manager.get_or_create_token.assert_called_once()

        # Verify token set
        assert os.environ["AUTH_TOKEN"] == "mock-jwt-token-rs256"

    @patch.dict(
        os.environ,
        {"FASTMCP_CLOUD": "true"},
        clear=False,
    )
    def test_generated_token_is_valid_jwt_rs256(self):
        """Verify generated token is valid JWT with RS256 algorithm."""
        # Clear tokens
        for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
            if key in os.environ:
                del os.environ[key]

        from server import ensure_cloud_auth_token

        # Call function
        ensure_cloud_auth_token()

        # Get generated token
        token = os.environ.get("AUTH_TOKEN")
        assert token is not None

        # Decode without verification to check structure
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})

            # Verify standard claims
            assert "iss" in decoded  # Issuer
            assert "aud" in decoded  # Audience
            assert "exp" in decoded  # Expiration
            assert "iat" in decoded  # Issued at

            # Verify header contains RS256
            header = jwt.get_unverified_header(token)
            assert header.get("alg") == "RS256"

        except jwt.DecodeError as e:
            pytest.fail(f"Generated token is not valid JWT: {e}")


class TestGetAuthProvider:
    """Test get_auth_provider() behavior in cloud vs local mode."""

    @patch.dict(os.environ, {"FASTMCP_CLOUD": "true"}, clear=False)
    def test_get_auth_provider_returns_none_in_cloud(self):
        """Verify get_auth_provider() returns None when FASTMCP_CLOUD=true."""
        from server import get_auth_provider

        auth_provider = get_auth_provider()

        # In cloud mode, should return None (delegates to cloud middleware)
        assert auth_provider is None

    @patch.dict(os.environ, {"FASTMCP_CLOUD": "false"}, clear=False)
    def test_get_auth_provider_returns_jwt_verifier_local(self):
        """Verify get_auth_provider() returns JWTVerifier in local mode."""
        from server import get_auth_provider

        auth_provider = get_auth_provider()

        # In local mode, should return JWTVerifier instance
        from fastmcp.server.auth.providers.jwt import JWTVerifier

        assert isinstance(auth_provider, JWTVerifier)


class TestCloudAuthenticationLogging:
    """Test logging output for cloud authentication."""

    @patch.dict(
        os.environ,
        {"FASTMCP_CLOUD": "true"},
        clear=False,
    )
    @patch("builtins.print")
    def test_cloud_auth_logs_token_generation(self, mock_print):
        """Verify console output when AUTH_TOKEN is generated."""
        # Clear tokens
        for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
            if key in os.environ:
                del os.environ[key]

        from server import ensure_cloud_auth_token

        # Call function
        ensure_cloud_auth_token()

        # Verify print was called with expected message
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "AUTH_TOKEN gerado automaticamente para FastMCP Cloud" in call_args
        assert "🔐" in call_args


class TestTokenPrioritization:
    """Test token prioritization logic.

    Tests AUTH_TOKEN vs FASTMCP_SERVER_AUTH vs MCP_AUTH_TOKEN priority.
    """

    @patch.dict(
        os.environ,
        {
            "FASTMCP_CLOUD": "true",
            "AUTH_TOKEN": "priority-1",
            "FASTMCP_SERVER_AUTH": "priority-2",
        },
        clear=False,
    )
    def test_existing_auth_token_has_highest_priority(self):
        """Verify AUTH_TOKEN not overwritten with FASTMCP_SERVER_AUTH."""
        from server import ensure_cloud_auth_token

        original_token = os.environ["AUTH_TOKEN"]

        # Call function
        ensure_cloud_auth_token()

        # AUTH_TOKEN should remain unchanged
        assert os.environ["AUTH_TOKEN"] == original_token

    @patch.dict(
        os.environ,
        {
            "FASTMCP_CLOUD": "true",
            "FASTMCP_SERVER_AUTH": "server-level-auth",
        },
        clear=False,
    )
    def test_fastmcp_server_auth_prevents_generation(self):
        """Verify FASTMCP_SERVER_AUTH prevents new AUTH_TOKEN generation."""
        # Ensure AUTH_TOKEN doesn't exist
        if "AUTH_TOKEN" in os.environ:
            del os.environ["AUTH_TOKEN"]

        from server import ensure_cloud_auth_token

        # Call function
        ensure_cloud_auth_token()

        # AUTH_TOKEN should NOT be generated
        assert "AUTH_TOKEN" not in os.environ or os.environ.get("AUTH_TOKEN") == ""
        # FASTMCP_SERVER_AUTH should remain
        assert os.environ["FASTMCP_SERVER_AUTH"] == "server-level-auth"


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    @patch.dict(os.environ, {}, clear=True)
    def test_local_mode_unchanged(self):
        """Verify local mode (non-cloud) behavior is unchanged."""
        # Without FASTMCP_CLOUD, should work as before
        from server import get_auth_provider

        auth_provider = get_auth_provider()

        # Should return JWTVerifier for local authentication
        from fastmcp.server.auth.providers.jwt import JWTVerifier

        assert isinstance(auth_provider, JWTVerifier)

    @patch.dict(os.environ, {"FASTMCP_CLOUD": "false"}, clear=False)
    def test_explicit_false_preserves_local_behavior(self):
        """Verify FASTMCP_CLOUD=false preserves local authentication."""
        from server import get_auth_provider

        auth_provider = get_auth_provider()

        # Should still use JWTVerifier
        from fastmcp.server.auth.providers.jwt import JWTVerifier

        assert isinstance(auth_provider, JWTVerifier)
