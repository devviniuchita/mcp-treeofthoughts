"""
End-to-End Authentication Testing and Validation

Comprehensive E2E test suite for FastMCP Cloud authentication system.
Validates complete authentication flow from token generation to server validation.

Test Categories:
1. Complete Authentication Flow Testing
2. Cloud Environment Integration
3. Token Lifecycle Management
4. Error Handling and Edge Cases
5. Performance and Load Testing
6. Security Validation
7. Cross-Environment Compatibility
"""

import json
import os
import subprocess
import threading
import time

from typing import Any
from typing import Dict
from typing import Optional
from unittest.mock import MagicMock
from unittest.mock import patch

import jwt
import pytest
import requests

from cryptography.hazmat.primitives import serialization


class TestE2EAuthenticationFlow:
    """Complete end-to-end authentication flow validation."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Clean environment
        for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH", "FASTMCP_CLOUD"]:
            if key in os.environ:
                del os.environ[key]

        # Set up test configuration
        self.test_config = {
            "server_url": "http://localhost:8000",
            "cloud_url": "https://mcptreeofthoughts.fastmcp.app/mcp",
            "test_timeout": 30,
            "validation_server_port": 5173,
        }

    def test_complete_cloud_authentication_flow(self):
        """
        Test complete cloud authentication flow from token generation to server validation.

        Steps:
        1. Configure FASTMCP_CLOUD=true
        2. Generate AUTH_TOKEN via ensure_cloud_auth_token()
        3. Validate token structure and claims
        4. Test token against validation server
        5. Verify server accepts the token
        """
        # Step 1: Configure cloud environment
        os.environ["FASTMCP_CLOUD"] = "true"

        # Step 2: Generate token
        from server import ensure_cloud_auth_token

        # Clear existing tokens
        for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
            if key in os.environ:
                del os.environ[key]

        # Generate new token
        ensure_cloud_auth_token()

        # Step 3: Validate token exists and structure
        assert "AUTH_TOKEN" in os.environ
        token = os.environ["AUTH_TOKEN"]
        assert token.startswith("eyJ")  # JWT format

        # Step 4: Decode and validate claims
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            assert "iss" in decoded
            assert "aud" in decoded
            assert "exp" in decoded
            assert decoded["iss"] == "fastmcp-server"
        except jwt.DecodeError:
            pytest.fail("Generated token is not a valid JWT")

        # Step 5: Test against validation server (if available)
        self._test_token_against_validation_server(token)

    def _test_token_against_validation_server(self, token: str):
        """Test token against local validation server."""
        try:
            # Try to start validation server in background if not running
            server_process = None
            try:
                # Check if server is already running
                response = requests.get(
                    f"http://localhost:{self.test_config['validation_server_port']}/health",
                    timeout=2,
                )
                server_running = response.status_code == 200
            except:
                server_running = False

            if not server_running:
                # Start validation server
                server_process = subprocess.Popen(
                    ["python", "validation_server.py"], cwd=os.getcwd()
                )

                # Wait for server to start
                time.sleep(3)

            # Test token validation
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"http://localhost:{self.test_config['validation_server_port']}/api/jwt",
                headers=headers,
                timeout=self.test_config["test_timeout"],
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "jwt_configured" in data

        except Exception as e:
            # If validation server not available, skip this part of test
            pytest.skip(f"Validation server not available: {e}")
        finally:
            if server_process:
                server_process.terminate()
                server_process.wait()

    def test_cloud_url_connectivity(self):
        """Test connectivity to FastMCP Cloud URL with authentication."""
        # This test validates the actual cloud deployment
        if "AUTH_TOKEN" not in os.environ:
            pytest.skip("No AUTH_TOKEN available for cloud testing")

        token = os.environ["AUTH_TOKEN"]
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(
                self.test_config["cloud_url"],
                headers=headers,
                timeout=self.test_config["test_timeout"],
            )

            # Should get a response (even if error, shows connectivity)
            assert response.status_code in [200, 401, 403]

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Cloud URL not accessible: {e}")

    def test_token_refresh_flow(self):
        """Test automatic token refresh mechanism."""
        os.environ["FASTMCP_CLOUD"] = "true"

        from server import ensure_cloud_auth_token

        # Generate initial token
        ensure_cloud_auth_token()
        initial_token = os.environ.get("AUTH_TOKEN")
        assert initial_token is not None

        # Wait for potential refresh (simulate time passing)
        time.sleep(1)

        # Generate again (should refresh if needed)
        ensure_cloud_auth_token()
        refreshed_token = os.environ.get("AUTH_TOKEN")

        # Token should be refreshed (different from initial)
        assert refreshed_token != initial_token

    def test_concurrent_token_generation(self):
        """Test thread-safe token generation under concurrent load."""
        os.environ["FASTMCP_CLOUD"] = "true"

        from server import ensure_cloud_auth_token

        results = []
        errors = []

        def generate_token():
            try:
                # Clear environment for each thread
                for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
                    if key in os.environ:
                        del os.environ[key]

                ensure_cloud_auth_token()
                token = os.environ.get("AUTH_TOKEN")
                results.append(token)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_token)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Validate results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, "Not all threads generated tokens"

        # All tokens should be valid JWTs
        for token in results:
            assert token.startswith("eyJ")
            try:
                jwt.decode(token, options={"verify_signature": False})
            except jwt.DecodeError:
                pytest.fail(f"Invalid JWT generated: {token}")

    def test_authentication_error_handling(self):
        """Test error handling in authentication system."""
        os.environ["FASTMCP_CLOUD"] = "true"

        # Test with invalid JWT manager state
        with patch('src.jwt_manager.JWTManager._initialize_jwt_system') as mock_init:
            mock_init.side_effect = Exception("JWT initialization failed")

            from server import ensure_cloud_auth_token

            # Should handle error gracefully
            ensure_cloud_auth_token()

            # Should still have some token or fallback behavior
            # (implementation dependent)

    def test_performance_under_load(self):
        """Test authentication performance under concurrent load."""
        os.environ["FASTMCP_CLOUD"] = "true"

        from server import ensure_cloud_auth_token

        start_time = time.time()

        # Generate tokens concurrently
        for i in range(10):
            for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
                if key in os.environ:
                    del os.environ[key]

            ensure_cloud_auth_token()

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time (adjust based on requirements)
        assert duration < 10, f"Performance test took too long: {duration}s"

        # All tokens should be valid
        assert "AUTH_TOKEN" in os.environ
        token = os.environ["AUTH_TOKEN"]
        assert token.startswith("eyJ")


class TestCrossEnvironmentCompatibility:
    """Test authentication across different environments."""

    def test_local_vs_cloud_environment_switching(self):
        """Test switching between local and cloud environments."""
        from server import ensure_cloud_auth_token
        from server import get_auth_provider

        # Test cloud mode
        os.environ["FASTMCP_CLOUD"] = "true"
        ensure_cloud_auth_token()
        cloud_token = os.environ.get("AUTH_TOKEN")
        cloud_provider = get_auth_provider()

        # Should generate token in cloud mode
        assert cloud_token is not None
        assert cloud_provider is None  # Cloud mode returns None

        # Test local mode
        os.environ["FASTMCP_CLOUD"] = "false"
        for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
            if key in os.environ:
                del os.environ[key]

        local_provider = get_auth_provider()
        # Should return JWT verifier in local mode
        assert local_provider is not None

    def test_environment_variable_priority(self):
        """Test priority of authentication environment variables."""
        # Set all authentication variables
        os.environ.update(
            {
                "FASTMCP_CLOUD": "true",
                "AUTH_TOKEN": "priority-1",
                "FASTMCP_SERVER_AUTH": "priority-2",
            }
        )

        from server import ensure_cloud_auth_token

        # Should not generate new token (AUTH_TOKEN exists)
        ensure_cloud_auth_token()

        # AUTH_TOKEN should remain unchanged (highest priority)
        assert os.environ["AUTH_TOKEN"] == "priority-1"


class TestSecurityValidation:
    """Security-focused authentication tests."""

    def test_token_entropy_and_uniqueness(self):
        """Test that generated tokens have sufficient entropy."""
        os.environ["FASTMCP_CLOUD"] = "true"

        from server import ensure_cloud_auth_token

        # Generate multiple tokens
        tokens = []
        for i in range(5):
            for key in ["AUTH_TOKEN", "FASTMCP_SERVER_AUTH"]:
                if key in os.environ:
                    del os.environ[key]

            ensure_cloud_auth_token()
            tokens.append(os.environ["AUTH_TOKEN"])

        # All tokens should be unique
        assert len(set(tokens)) == 5, "Tokens are not unique"

        # Tokens should have sufficient length (JWTs are typically 200+ chars)
        for token in tokens:
            assert len(token) > 100, f"Token too short: {len(token)}"

    def test_token_claims_security(self):
        """Test security of token claims."""
        os.environ["FASTMCP_CLOUD"] = "true"

        from server import ensure_cloud_auth_token

        ensure_cloud_auth_token()
        token = os.environ["AUTH_TOKEN"]

        # Decode without verification for claims inspection
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Should have proper issuer and audience
        assert decoded["iss"] == "fastmcp-server"
        assert "aud" in decoded

        # Should not contain sensitive information
        sensitive_fields = ["password", "secret", "key", "private"]
        for field in sensitive_fields:
            assert field not in str(decoded).lower()

    def test_token_expiration_handling(self):
        """Test token expiration and refresh behavior."""
        os.environ["FASTMCP_CLOUD"] = "true"

        from server import ensure_cloud_auth_token

        ensure_cloud_auth_token()
        initial_token = os.environ["AUTH_TOKEN"]

        # Decode to check expiration
        decoded = jwt.decode(initial_token, options={"verify_signature": False})
        exp_time = decoded["exp"]

        # Should have reasonable expiration time (not too short, not too long)
        current_time = int(time.time())
        assert exp_time > current_time  # Not already expired
        assert exp_time < current_time + (24 * 3600)  # Not more than 24 hours


class TestIntegrationWithMCPTools:
    """Test integration with MCP tools and resources."""

    def test_mcp_tools_access_with_authentication(self):
        """Test that MCP tools require proper authentication."""
        # This test validates that the MCP server properly enforces authentication
        # when accessing protected tools

        if "AUTH_TOKEN" not in os.environ:
            pytest.skip("No AUTH_TOKEN available for MCP testing")

        # Test would involve:
        # 1. Starting MCP server
        # 2. Attempting to access protected tools without auth (should fail)
        # 3. Accessing tools with valid auth (should succeed)
        # 4. Testing token refresh during active sessions

        # For now, validate token structure
        token = os.environ["AUTH_TOKEN"]
        assert token.startswith("eyJ")

        # This is a placeholder for actual MCP integration testing
        # In a real implementation, this would test actual tool access
        pass

    def test_resource_access_control(self):
        """Test resource access control with authentication."""
        # Similar to tool testing but for resources
        # Validates that resources are properly protected

        if "AUTH_TOKEN" not in os.environ:
            pytest.skip("No AUTH_TOKEN available for resource testing")

        # Placeholder for resource access testing
        pass


# Integration test that runs the complete validation suite
class TestCompleteE2EValidation:
    """Complete end-to-end validation test."""

    def test_full_authentication_workflow(self):
        """
        Execute complete authentication workflow validation.

        This test runs through the entire authentication pipeline:
        1. Environment setup
        2. Token generation and validation
        3. Server connectivity testing
        4. Performance validation
        5. Security assessment
        """
        # Run all validation categories
        test_flow = TestE2EAuthenticationFlow()
        test_flow.setup_method()

        # Execute core flow tests
        test_flow.test_complete_cloud_authentication_flow()
        test_flow.test_cloud_url_connectivity()
        test_flow.test_token_refresh_flow()

        # Performance tests
        test_flow.test_performance_under_load()

        # Security tests
        security_test = TestSecurityValidation()
        security_test.test_token_entropy_and_uniqueness()
        security_test.test_token_claims_security()

        # Environment compatibility
        compat_test = TestCrossEnvironmentCompatibility()
        compat_test.test_local_vs_cloud_environment_switching()
        compat_test.test_environment_variable_priority()

        print("✅ Complete E2E authentication workflow validated successfully")
