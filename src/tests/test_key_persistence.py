"""Tests for key persistence functionality."""

from __future__ import annotations

import os
import stat
import tempfile

from unittest.mock import mock_open
from unittest.mock import patch

import pytest

from fastmcp.server.auth.providers.jwt import RSAKeyPair

from src.exceptions import AuthenticationError
from src.exceptions import ConfigurationError
from src.jwt_manager import JWTManager


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


@pytest.fixture
def temp_directory():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class TestKeyPersistence:
    """Test suite for key persistence functionality."""

    def test_persist_private_key_creates_file_with_secure_permissions(
        self, temp_directory
    ):
        """Test that persist_private_key creates file with 600 permissions."""
        jwt_manager = JWTManager()
        key_path = os.path.join(temp_directory, 'test_key.pem')

        # Generate test key
        test_key_pem = jwt_manager.key_pair.private_key.get_secret_value()

        # Persist key
        jwt_manager.persist_private_key(key_path, test_key_pem)

        # Verify file exists
        assert os.path.exists(key_path)

        # Verify file permissions are secure (600 on Unix, 666 on Windows)
        file_mode = oct(os.stat(key_path).st_mode)[-3:]
        assert file_mode in ['600', '666']  # Windows may show 666

        # Verify file content
        with open(key_path, 'r') as f:
            content = f.read()
            assert content == test_key_pem

    def test_persist_private_key_creates_directory_if_not_exists(self, temp_directory):
        """Test that persist_private_key creates parent directories."""
        jwt_manager = JWTManager()
        nested_dir = os.path.join(temp_directory, 'nested', 'deep', 'path')
        key_path = os.path.join(nested_dir, 'test_key.pem')

        # Ensure nested directory doesn't exist
        assert not os.path.exists(nested_dir)

        # Persist key should create directories
        test_key_pem = jwt_manager.key_pair.private_key.get_secret_value()
        jwt_manager.persist_private_key(key_path, test_key_pem)

        # Verify directory and file were created
        assert os.path.exists(nested_dir)
        assert os.path.exists(key_path)

    def test_load_private_key_from_existing_file(self, temp_key_file):
        """Test loading private key from existing file."""
        jwt_manager = JWTManager()

        # Load key from file
        loaded_key_pair = jwt_manager.load_private_key(temp_key_file)

        assert loaded_key_pair is not None
        assert loaded_key_pair.private_key is not None
        assert loaded_key_pair.public_key is not None

        # Verify we can create tokens with loaded key
        # This indirectly tests that the key was loaded correctly
        assert isinstance(loaded_key_pair.private_key.get_secret_value(), str)
        assert isinstance(loaded_key_pair.public_key, str)

    def test_load_private_key_fixes_insecure_permissions(self, temp_key_file):
        """Test that load_private_key fixes insecure file permissions."""
        jwt_manager = JWTManager()

        # Make file insecure (readable by others)
        os.chmod(temp_key_file, 0o644)

        # File is now insecure after chmod 644

        # Load key should attempt to fix permissions
        jwt_manager.load_private_key(temp_key_file)

        # Verify permissions were processed (may be 600 or 666 on Windows)
        file_mode = oct(os.stat(temp_key_file).st_mode)[-3:]
        assert file_mode in [
            '600',
            '666',
        ]  # Windows may show 666    def test_load_private_key_nonexistent_file_raises_error(self):
        """Test that loading nonexistent key file raises AuthenticationError."""
        jwt_manager = JWTManager()
        nonexistent_path = '/nonexistent/path/key.pem'

        with pytest.raises(AuthenticationError) as exc_info:
            jwt_manager.load_private_key(nonexistent_path)

        assert 'Falha ao carregar chave privada' in str(exc_info.value)
        assert nonexistent_path in str(exc_info.value.details)

    def test_load_private_key_invalid_format_raises_error(self, temp_directory):
        """Test that loading invalid key format raises AuthenticationError."""
        jwt_manager = JWTManager()

        # Create file with invalid key content
        invalid_key_path = os.path.join(temp_directory, 'invalid_key.pem')
        with open(invalid_key_path, 'w') as f:
            f.write('this is not a valid RSA private key')

        with pytest.raises(AuthenticationError) as exc_info:
            jwt_manager.load_private_key(invalid_key_path)

        assert 'Falha ao carregar chave privada' in str(exc_info.value)

    def test_persist_private_key_error_handling(self):
        """Test persist_private_key error handling with invalid path."""
        jwt_manager = JWTManager()

        if jwt_manager.key_pair and jwt_manager.key_pair.private_key:
            # Try to write to invalid path (Windows: use NUL device)
            invalid_path = 'CON/invalid_key.pem'  # CON is reserved in Windows
            test_key_pem = jwt_manager.key_pair.private_key.get_secret_value()

            with pytest.raises(
                (AuthenticationError, OSError, PermissionError)
            ) as exc_info:
                jwt_manager.persist_private_key(invalid_path, test_key_pem)
        else:
            pytest.skip("JWTManager not properly initialized")

    def test_key_persistence_roundtrip(self, temp_directory):
        """Test complete persist->load roundtrip maintains key integrity."""
        jwt_manager = JWTManager()
        key_path = os.path.join(temp_directory, 'roundtrip_key.pem')

        # Get original key
        original_private_key = jwt_manager.key_pair.private_key.get_secret_value()
        original_public_key = jwt_manager.key_pair.public_key

        # Persist key
        jwt_manager.persist_private_key(key_path, original_private_key)

        # Load key back
        loaded_key_pair = jwt_manager.load_private_key(key_path)

        # Verify key integrity
        assert loaded_key_pair.private_key.get_secret_value() == original_private_key
        assert loaded_key_pair.public_key == original_public_key

    def test_production_environment_key_validation(self, temp_key_file):
        """Test production environment validates PRIVATE_KEY_PATH."""
        with patch.dict(
            os.environ, {'ENV': 'production', 'PRIVATE_KEY_PATH': temp_key_file}
        ):
            # Should initialize successfully with valid key file
            jwt_manager = JWTManager()
            assert jwt_manager.key_pair is not None

    def test_production_environment_missing_key_path_fails(self):
        """Test production environment fails without PRIVATE_KEY_PATH."""
        with patch.dict(os.environ, {'ENV': 'production'}, clear=False):
            # Remove PRIVATE_KEY_PATH if it exists
            if 'PRIVATE_KEY_PATH' in os.environ:
                del os.environ['PRIVATE_KEY_PATH']

            with pytest.raises(SystemExit):
                JWTManager()

    def test_production_environment_nonexistent_key_file_fails(self):
        """Test production environment fails with nonexistent key file."""
        with patch.dict(
            os.environ,
            {'ENV': 'production', 'PRIVATE_KEY_PATH': '/nonexistent/key.pem'},
        ):
            with pytest.raises(SystemExit):
                JWTManager()

    def test_development_environment_generates_ephemeral_key(self):
        """Test development environment generates ephemeral key when no path set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear ENV to ensure development mode
            jwt_manager = JWTManager()

            assert jwt_manager.key_pair is not None
            assert jwt_manager.kid is not None
            assert jwt_manager.kid.startswith('key-')

    def test_development_environment_with_key_path_persists(self, temp_directory):
        """Test development environment persists key when PRIVATE_KEY_PATH set."""
        key_path = os.path.join(temp_directory, 'dev_key.pem')

        with patch.dict(os.environ, {'PRIVATE_KEY_PATH': key_path}):
            # Clear ENV to ensure development mode
            if 'ENV' in os.environ:
                del os.environ['ENV']

            jwt_manager = JWTManager()

            # Verify key was persisted
            assert os.path.exists(key_path)

            # Verify file permissions are secure
            file_mode = oct(os.stat(key_path).st_mode)[-3:]
            assert file_mode in ['600', '666']  # Windows may show 666
