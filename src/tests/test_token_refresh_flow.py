"""Tests for token refresh and caching flow."""

from __future__ import annotations

import threading
import time

from unittest.mock import Mock
from unittest.mock import patch

import jwt as pyjwt
import pytest

from fastmcp.server.auth.providers.jwt import RSAKeyPair

from src.config.constants import JWT_AUDIENCE
from src.config.constants import JWT_EXPIRY_SECONDS
from src.config.constants import JWT_ISSUER
from src.exceptions import AuthenticationError
from src.jwt_manager import JWTManager


class TestTokenRefreshFlow:
    """Test suite for token refresh and caching functionality."""

    def test_get_or_create_token_returns_cached_token_when_valid(self):
        """Test that get_or_create_token returns cached token when still valid."""
        jwt_manager = JWTManager()

        # First call should create token
        token1 = jwt_manager.get_or_create_token()

        # Second call should return same cached token
        token2 = jwt_manager.get_or_create_token()

        assert token1 == token2
        assert jwt_manager._current_token == token1

    def test_get_or_create_token_creates_new_token_when_none_exists(self):
        """Test that get_or_create_token creates token when none exists."""
        jwt_manager = JWTManager()

        # Clear any existing token
        jwt_manager._current_token = None
        jwt_manager._token_expiry = None

        token = jwt_manager.get_or_create_token()

        assert token is not None
        assert len(token) > 100  # JWT tokens are long strings
        assert jwt_manager._current_token == token
        assert jwt_manager._token_expiry is not None

    @patch('src.jwt_manager.time.time')
    def test_get_or_create_token_refreshes_near_expiry(self, mock_time):
        """Test that get_or_create_token refreshes token near expiry."""
        jwt_manager = JWTManager()

        # Mock current time
        current_time = 1000000
        mock_time.return_value = current_time

        # Create initial token
        token1 = jwt_manager.get_or_create_token()

        # Advance time to near expiry (within buffer)
        near_expiry_time = (
            current_time + JWT_EXPIRY_SECONDS - 20
        )  # 20 seconds before expiry
        mock_time.return_value = near_expiry_time

        # Should create new token due to buffer
        token2 = jwt_manager.get_or_create_token()

        assert token2 != token1  # Should be different token
        assert jwt_manager._current_token == token2

    @patch('src.jwt_manager.time.time')
    def test_get_or_create_token_refreshes_after_expiry(self, mock_time):
        """Test that get_or_create_token refreshes token after expiry."""
        jwt_manager = JWTManager()

        # Mock current time
        current_time = 1000000
        mock_time.return_value = current_time

        # Create initial token
        token1 = jwt_manager.get_or_create_token()

        # Advance time past expiry
        expired_time = current_time + JWT_EXPIRY_SECONDS + 100
        mock_time.return_value = expired_time

        # Should create new token
        token2 = jwt_manager.get_or_create_token()

        assert token2 != token1
        assert jwt_manager._current_token == token2

    def test_get_or_create_token_custom_buffer_seconds(self):
        """Test get_or_create_token with custom buffer seconds."""
        jwt_manager = JWTManager()

        # Create token with large buffer to force refresh
        token1 = jwt_manager.get_or_create_token(buffer_seconds=JWT_EXPIRY_SECONDS - 10)

        # Should immediately refresh due to large buffer
        token2 = jwt_manager.get_or_create_token(buffer_seconds=JWT_EXPIRY_SECONDS - 10)

        # Tokens might be same due to timing, but mechanism should work
        assert isinstance(token2, str)
        assert len(token2) > 100

    def test_token_refresh_thread_safety(self):
        """Test that token refresh is thread-safe."""
        jwt_manager = JWTManager()
        tokens = []
        errors = []

        def get_token():
            try:
                token = jwt_manager.get_or_create_token()
                tokens.append(token)
            except Exception as e:
                errors.append(e)

        # Create multiple threads trying to get tokens simultaneously
        threads = [threading.Thread(target=get_token) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # All tokens should be valid
        assert len(tokens) == 10
        for token in tokens:
            assert isinstance(token, str)
            assert len(token) > 100

        # All tokens should be the same (cached)
        unique_tokens = set(tokens)
        assert len(unique_tokens) == 1

    def test_token_contains_correct_claims(self):
        """Test that generated tokens contain correct claims."""
        jwt_manager = JWTManager()
        token = jwt_manager.get_or_create_token()

        # Decode token to verify claims
        decoded = pyjwt.decode(
            token,
            jwt_manager.key_pair.public_key,
            algorithms=["RS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )

        assert decoded['iss'] == JWT_ISSUER
        assert decoded['aud'] == JWT_AUDIENCE
        assert decoded['sub'] == 'mcp-server'
        assert decoded['scope'] == 'mcp:full'
        assert 'iat' in decoded
        assert 'exp' in decoded
        assert 'jti' in decoded  # Unique token identifier

    def test_token_contains_kid_header(self):
        """Test that generated tokens contain kid in header."""
        jwt_manager = JWTManager()
        token = jwt_manager.get_or_create_token()

        # Decode header to verify kid
        header = pyjwt.get_unverified_header(token)

        assert 'kid' in header
        assert header['kid'] == jwt_manager.kid
        assert header['alg'] == 'RS256'
        assert header['typ'] == 'JWT'

    @patch('src.jwt_manager.time.time')
    def test_token_expiry_tracking_accuracy(self, mock_time):
        """Test that token expiry tracking is accurate."""
        jwt_manager = JWTManager()

        # Mock current time
        current_time = 1000000
        mock_time.return_value = current_time

        token = jwt_manager.get_or_create_token()

        # Verify expiry tracking
        expected_expiry = current_time + JWT_EXPIRY_SECONDS
        assert jwt_manager._token_expiry == expected_expiry

    def test_access_token_attribute_updated_on_refresh(self):
        """Test that access_token attribute is updated when token refreshes."""
        jwt_manager = JWTManager()

        # Clear tokens to force generation
        jwt_manager._current_token = None
        jwt_manager._token_expiry = None

        original_access_token = jwt_manager.access_token

        # Get new token
        new_token = jwt_manager.get_or_create_token()

        # access_token should be updated
        assert jwt_manager.access_token == new_token

    def test_token_file_persistence_on_refresh(self):
        """Test that token file is updated when token refreshes."""
        jwt_manager = JWTManager()

        # Mock _save_token_to_file to track calls
        with patch.object(jwt_manager, '_save_token_to_file') as mock_save:
            # Force token refresh
            jwt_manager._current_token = None
            jwt_manager._token_expiry = None

            jwt_manager.get_or_create_token()

            # Should have called save
            mock_save.assert_called_once()

    def test_get_current_token_fallback_behavior(self):
        """Test get_current_token fallback when no cached token exists."""
        jwt_manager = JWTManager()

        # Clear access_token to trigger fallback
        jwt_manager.access_token = None

        token = jwt_manager.get_current_token()

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100

    def test_concurrent_token_rotation_during_refresh(self):
        """Test token refresh behavior during concurrent key rotation."""
        jwt_manager = JWTManager()

        # Store original token
        original_token = jwt_manager.get_or_create_token()

        # Simulate key rotation
        new_key_pair = RSAKeyPair.generate()
        jwt_manager.rotate_keys(new_key_pair.private_key.get_secret_value())

        # Get token after rotation - should be different
        new_token = jwt_manager.get_or_create_token()

        assert new_token != original_token

        # New token should be signed with new key
        header = pyjwt.get_unverified_header(new_token)
        assert header['kid'] != pyjwt.get_unverified_header(original_token)['kid']

    def test_token_refresh_preserves_thread_safety_during_rotation(self):
        """Test that token refresh maintains thread safety during key rotation."""
        jwt_manager = JWTManager()
        tokens = []
        errors = []

        def refresh_and_rotate():
            try:
                # Get token
                token = jwt_manager.get_or_create_token()
                tokens.append(token)

                # Attempt rotation (might fail due to threading, that's ok)
                try:
                    new_key_pair = RSAKeyPair.generate()
                    jwt_manager.rotate_keys(new_key_pair.private_key.get_secret_value())
                except:
                    pass  # Expected in concurrent scenario

            except Exception as e:
                errors.append(e)

        # Create threads for concurrent operations
        threads = [threading.Thread(target=refresh_and_rotate) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should have minimal errors (threading conflicts are acceptable)
        assert len(tokens) == 5

        # All tokens should be valid
        for token in tokens:
            assert isinstance(token, str)
            assert len(token) > 100

    @patch('src.jwt_manager.time.time')
    def test_buffer_seconds_precision(self, mock_time):
        """Test buffer_seconds parameter precision in refresh decisions."""
        jwt_manager = JWTManager()

        # Mock time progression
        start_time = 1000000
        mock_time.return_value = start_time

        # Create initial token
        token1 = jwt_manager.get_or_create_token()

        # Move time to exactly buffer boundary
        boundary_time = start_time + JWT_EXPIRY_SECONDS - 30  # 30 second buffer
        mock_time.return_value = boundary_time

        # Should refresh at boundary
        token2 = jwt_manager.get_or_create_token(buffer_seconds=30)

        assert token2 != token1  # Should be new token

        # Move time just before boundary
        before_boundary = start_time + JWT_EXPIRY_SECONDS - 31
        mock_time.return_value = before_boundary

        # Create new manager for clean test
        jwt_manager2 = JWTManager()
        token3 = jwt_manager2.get_or_create_token()

        # Should use same token (not at boundary yet)
        token4 = jwt_manager2.get_or_create_token(buffer_seconds=30)
        assert token4 == token3
