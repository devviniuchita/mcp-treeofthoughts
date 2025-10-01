"""Tests for JWKS endpoint functionality."""

from __future__ import annotations

import json
import os
import tempfile

from unittest.mock import patch

import pytest

from fastmcp.server.auth.providers.jwt import RSAKeyPair
from validation_server import app

from src.jwt_manager import JWTManager


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_key_file():
    """Create temporary key file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
        # Generate test RSA key
        key_pair = RSAKeyPair.generate()
        f.write(key_pair.private_key.get_secret_value())
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


class TestJWKSEndpoint:
    """Test suite for JWKS endpoint functionality."""

    def test_jwks_endpoint_returns_valid_json(self, client):
        """Test that JWKS endpoint returns valid JSON structure."""
        response = client.get('/.well-known/jwks.json')

        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'

        data = json.loads(response.data)
        assert 'keys' in data
        assert isinstance(data['keys'], list)
        assert len(data['keys']) >= 1  # At least current key

    def test_jwks_endpoint_has_proper_cache_headers(self, client):
        """Test that JWKS endpoint includes proper cache headers."""
        response = client.get('/.well-known/jwks.json')

        assert response.status_code == 200
        assert 'Cache-Control' in response.headers
        assert 'public' in response.headers['Cache-Control']
        assert 'max-age=3600' in response.headers['Cache-Control']
        assert 's-maxage=3600' in response.headers['Cache-Control']

    def test_jwks_endpoint_has_cors_headers(self, client):
        """Test that JWKS endpoint includes CORS headers."""
        response = client.get('/.well-known/jwks.json')

        assert response.status_code == 200
        assert response.headers.get('Access-Control-Allow-Origin') == '*'

    def test_jwks_key_structure_rfc_7517_compliant(self, client):
        """Test that JWK structure is RFC 7517 compliant."""
        response = client.get('/.well-known/jwks.json')

        assert response.status_code == 200
        data = json.loads(response.data)

        # Test first key structure
        key = data['keys'][0]

        # Required RSA fields per RFC 7517
        assert key['kty'] == 'RSA'
        assert key['use'] == 'sig'
        assert key['alg'] == 'RS256'
        assert 'kid' in key
        assert 'n' in key  # RSA modulus
        assert 'e' in key  # RSA exponent

        # kid should be non-empty string
        assert isinstance(key['kid'], str)
        assert len(key['kid']) > 0

    def test_jwks_endpoint_with_key_rotation(self, client, temp_key_file):
        """Test JWKS endpoint during key rotation (multiple keys)."""
        # Test key rotation scenario by mocking JWTManager with rotated state

        # Create manager and simulate rotation
        jwt_manager = JWTManager()
        original_kid = jwt_manager.kid

        # Perform key rotation
        new_key_pair = RSAKeyPair.generate()
        jwt_manager.rotate_keys(new_key_pair.private_key.get_secret_value())

        # Mock the JWKS endpoint to return our rotated manager
        with patch('src.jwt_manager.JWTManager') as mock_manager_class:
            mock_manager_class.return_value = jwt_manager

            response = client.get('/.well-known/jwks.json')
            assert response.status_code == 200
            data = json.loads(response.data)

            # Should have both current and previous keys
            assert len(data['keys']) == 2

            # Verify both keys have different kids
            kids = [key['kid'] for key in data['keys']]
            assert len(set(kids)) == 2  # All kids should be unique
            assert (
                original_kid in kids
            )  # Previous key should be present    def test_jwks_endpoint_error_handling(self, client):
        """Test JWKS endpoint error handling with invalid configuration."""
        # Mock JWTManager to raise an exception
        with patch('src.jwt_manager.JWTManager') as mock_jwt_manager:
            mock_jwt_manager.side_effect = Exception("Test error")

            response = client.get('/.well-known/jwks.json')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert 'message' in data
            assert data['error'] == 'internal_server_error'

    def test_jwks_endpoint_configuration_error_handling(self, client):
        """Test JWKS endpoint handling of configuration errors."""
        from src.exceptions import ConfigurationError

        # Mock JWTManager to raise ConfigurationError
        with patch('src.jwt_manager.JWTManager') as mock_jwt_manager:
            mock_jwt_manager.side_effect = ConfigurationError("JWT config error")

            response = client.get('/.well-known/jwks.json')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == 'jwks_unavailable'
            assert 'JWT config error' in data['details']

    def test_jwks_endpoint_cleanup_expired_keys(self, client):
        """Test that JWKS endpoint triggers cleanup of expired keys."""
        # Mock JWTManager methods
        with patch('src.jwt_manager.JWTManager') as mock_jwt_manager_class:
            mock_jwt_manager = mock_jwt_manager_class.return_value
            mock_jwt_manager.cleanup_expired_keys.return_value = True
            mock_jwt_manager.get_public_jwks.return_value = {"keys": []}

            response = client.get('/.well-known/jwks.json')

            assert response.status_code == 200
            # Verify cleanup was called
            mock_jwt_manager.cleanup_expired_keys.assert_called_once()
            mock_jwt_manager.get_public_jwks.assert_called_once()

    def test_jwks_endpoint_with_production_environment(self, client, temp_key_file):
        """Test JWKS endpoint behavior in production environment."""
        with patch.dict(
            os.environ, {'ENV': 'production', 'PRIVATE_KEY_PATH': temp_key_file}
        ):
            response = client.get('/.well-known/jwks.json')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'keys' in data
            assert len(data['keys']) >= 1

            # In production, should still return valid JWKS
            key = data['keys'][0]
            assert key['kty'] == 'RSA'
            assert key['use'] == 'sig'
            assert key['alg'] == 'RS256'
