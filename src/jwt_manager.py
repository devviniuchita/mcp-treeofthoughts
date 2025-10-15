"""JWT Configuration and Token Generation following enterprise security patterns."""

import json
import logging
import os
import threading
import time
import uuid

from typing import Any
from typing import Dict
from typing import Optional

import jwt

# Import custom auth providers (compatible with FastMCP 2.12.4)
from .auth_providers import JWTVerifier
from .auth_providers import RSAKeyPair


print("✅ Using custom auth providers compatible with FastMCP 2.12.4")

from .config.constants import JWT_AUDIENCE
from .config.constants import JWT_DEFAULT_SCOPES
from .config.constants import JWT_EXPIRY_SECONDS
from .config.constants import JWT_ISSUER
from .config.constants import TOKEN_FILE_PATH


# JWT Algorithm constant (RS256 for RSA signing)
JWT_ALGORITHM = "RS256"
JWT_EXPIRATION_SECONDS = JWT_EXPIRY_SECONDS
from .exceptions import AuthenticationError
from .exceptions import ConfigurationError
from .exceptions import TokenGenerationError


logger = logging.getLogger(__name__)


class JWTManager:
    """Professional JWT management following enterprise security patterns."""

    def __init__(self) -> None:
        self.auth_provider: Optional[JWTVerifier] = None
        self.access_token: Optional[str] = None
        self.key_pair: Optional[RSAKeyPair] = None
        self.kid: str = "default-key-id"  # Key ID for JWT headers
        self._current_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._lock = threading.RLock()  # Thread-safe token management

        # Key rotation support
        self.previous_key_pair: Optional[RSAKeyPair] = None
        self.previous_kid: Optional[str] = None
        self.rotation_timestamp: Optional[float] = None
        self.grace_period_seconds = 900  # 15 minutes grace period

        self._initialize_jwt_system()

    def _initialize_jwt_system(self) -> None:
        """Initialize JWT authentication system with proper error handling."""
        try:
            logger.info("🔐 Configurando autenticação JWT profissional...")

            # Check for existing private key first
            private_key_path = os.getenv("PRIVATE_KEY_PATH")
            
            # Enhanced logging for debugging CI issues
            logger.info(f"🔍 PRIVATE_KEY_PATH from environment: {private_key_path}")
            
            if private_key_path:
                logger.info(f"🔍 Checking if path exists: {private_key_path}")
                path_exists = os.path.exists(private_key_path)
                logger.info(f"🔍 Path exists: {path_exists}")
                
                if path_exists:
                    # Check if file is readable
                    if os.path.isfile(private_key_path) and os.access(private_key_path, os.R_OK):
                        logger.info(f"🔑 Carregando chave privada de: {private_key_path}")
                        self.key_pair = self.load_private_key(private_key_path)
                    else:
                        logger.error(f"❌ Arquivo não é legível: {private_key_path}")
                        raise ConfigurationError(
                            f"Arquivo de chave privada não é legível: {private_key_path}"
                        )
                else:
                    # Check if we're in production/CI and key is required
                    is_production = os.getenv("ENV", "").lower() == "production"
                    is_ci = os.getenv("CI", "").lower() == "true" or os.getenv("GITHUB_ACTIONS", "").lower() == "true"
                    
                    if is_production or is_ci:
                        logger.error(f"❌ PRIVATE_KEY_PATH definido mas arquivo não encontrado: {private_key_path}")
                        logger.error(f"❌ Diretório pai existe? {os.path.exists(os.path.dirname(private_key_path)) if os.path.dirname(private_key_path) else 'N/A'}")
                        raise ConfigurationError(
                            f"Arquivo de chave privada não encontrado: {private_key_path}. "
                            f"Verifique se a chave foi gerada corretamente no workflow."
                        )
                    
                    # Development mode: generate key and save to path
                    logger.info("🔑 Gerando novo par de chaves RSA (desenvolvimento)")
                    self.key_pair = RSAKeyPair.generate()
                    
                    # Try to persist the key
                    try:
                        self.persist_private_key(
                            private_key_path, self.key_pair.private_key.get_secret_value()
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Não foi possível persistir chave: {e}")
            else:
                # No PRIVATE_KEY_PATH specified - generate ephemeral key
                logger.info("🔑 PRIVATE_KEY_PATH não definido - gerando chave efêmera")
                self.key_pair = RSAKeyPair.generate()

            # Generate unique key ID
            import hashlib

            if self.key_pair and self.key_pair.public_key:
                key_hash = hashlib.sha256(
                    self.key_pair.public_key.encode('utf-8')
                ).hexdigest()[:8]
                self.kid = f"key-{key_hash}"
            else:
                raise ConfigurationError("Key pair not properly initialized")

            # Configure JWT verifier with security standards
            self.auth_provider = JWTVerifier(
                public_key=self.key_pair.public_key,
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
            )

            # Generate initial access token
            self.access_token = self._create_access_token()

            # Persist token for external access
            self._save_token_to_file()

            logger.info("✅ JWT Authentication configurado com sucesso!")
            logger.info(f"🔑 Key ID: {self.kid}")
            logger.info("🔑 ACCESS TOKEN gerado e salvo.")

        except Exception as e:
            logger.error(f"⚠️ Erro configurando JWT: {e}")
            raise ConfigurationError(
                "Falha na configuração do sistema JWT",
                details={"error": str(e)},
            ) from e

    def load_private_key(self, path: str) -> RSAKeyPair:
        """Load private key from file with secure permissions check."""
        try:
            import stat

            # Check file permissions (should be 600 or more restrictive)
            file_stat = os.stat(path)
            file_permissions = oct(file_stat.st_mode)[-3:]
            if file_permissions not in ['600', '400']:
                logger.warning(
                    f"⚠️ Private key file has insecure permissions: {file_permissions}"
                )
                # Attempt to fix permissions
                os.chmod(path, 0o600)
                logger.info("🔒 Fixed private key permissions to 600")

            # Read and load key
            with open(path, 'rb') as key_file:
                private_key_bytes = key_file.read()

            # Create RSAKeyPair from existing private key
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            private_key_obj = serialization.load_pem_private_key(
                private_key_bytes, password=None
            )

            if not isinstance(private_key_obj, rsa.RSAPrivateKey):
                raise ValueError("Invalid RSA private key format")

            # Convert back to PEM format for RSAKeyPair
            private_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            public_key_obj = private_key_obj.public_key()
            public_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            from pydantic import SecretStr

            return RSAKeyPair(
                private_key=SecretStr(private_pem.decode('utf-8')),
                public_key=public_pem.decode('utf-8'),
            )

        except Exception as e:
            logger.error(f"🚨 Erro carregando chave privada de {path}: {e}")
            raise AuthenticationError(
                f"Falha ao carregar chave privada de {path}",
                details={"error": str(e), "path": path},
            ) from e

    def persist_private_key(self, path: str, private_key_pem: str) -> None:
        """Persist private key to file with secure permissions."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Write private key to file
            with open(path, 'w') as key_file:
                key_file.write(private_key_pem)

            # Set secure permissions (600 = rw-------)
            os.chmod(path, 0o600)

            logger.info(f"🔐 Chave privada persistida em: {path}")
            logger.info("🔒 Permissões definidas para 600 (rw-------)")

        except Exception as e:
            logger.error(f"🚨 Erro persistindo chave privada em {path}: {e}")
            raise AuthenticationError(
                f"Falha ao persistir chave privada em {path}",
                details={"error": str(e), "path": path},
            ) from e

    def get_public_jwk(self) -> Dict[str, Any]:
        """Get public key in JWK format for JWKS endpoint."""
        try:
            import base64

            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            # Parse the public key
            if not self.key_pair or not self.key_pair.public_key:
                raise AuthenticationError("Key pair not initialized")

            public_key_obj = serialization.load_pem_public_key(
                self.key_pair.public_key.encode()
            )

            if not isinstance(public_key_obj, rsa.RSAPublicKey):
                raise ValueError("Invalid RSA public key")

            # Get RSA public numbers
            public_numbers = public_key_obj.public_numbers()

            # Convert to JWK format
            def _int_to_base64url(value: int) -> str:
                """Convert integer to base64url-encoded string."""
                # Calculate the number of bytes needed
                byte_length = (value.bit_length() + 7) // 8
                # Convert to bytes
                bytes_value = value.to_bytes(byte_length, 'big')
                # Encode as base64url
                return base64.urlsafe_b64encode(bytes_value).decode('utf-8').rstrip('=')

            jwk = {
                "kty": "RSA",
                "use": "sig",
                "kid": self.kid,
                "alg": "RS256",
                "n": _int_to_base64url(public_numbers.n),
                "e": _int_to_base64url(public_numbers.e),
            }

            return jwk

        except Exception as e:
            logger.error(f"🚨 Erro gerando JWK: {e}")
            raise AuthenticationError(
                "Falha ao gerar JWK da chave pública", details={"error": str(e)}
            ) from e

    def get_or_create_token(self, buffer_seconds: int = 30) -> str:
        """Get current token or create new one if expired/near expiry (thread-safe)."""
        with self._lock:
            current_time = time.time()

            # Check if we need a new token (expired or near expiry)
            if (
                self._current_token is None
                or self._token_expiry is None
                or current_time >= (self._token_expiry - buffer_seconds)
            ):

                logger.info(
                    "🔄 Gerando novo token JWT (expirado ou próximo do vencimento)"
                )
                self._current_token = self._create_access_token()
                self._token_expiry = current_time + JWT_EXPIRATION_SECONDS

                # Update the main access_token attribute
                self.access_token = self._current_token

                # Persist token for external access
                self._save_token_to_file()

            return self._current_token

    def _create_access_token(self) -> str:
        """Create access token with enterprise security standards."""
        try:
            payload = {
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "sub": "mcp-server",
                "scope": "mcp:full",
                "iat": int(time.time()),
                "exp": int(time.time()) + JWT_EXPIRATION_SECONDS,
                "jti": str(uuid.uuid4()),  # Unique token identifier
            }

            headers = {
                "typ": "JWT",
                "alg": JWT_ALGORITHM,
            }

            # Add kid (key ID) to headers if available
            if hasattr(self, 'kid') and self.kid:
                headers["kid"] = self.kid

            if not self.key_pair or not self.key_pair.private_key:
                raise AuthenticationError("Key pair not initialized")

            token = jwt.encode(
                payload=payload,
                key=self.key_pair.private_key.get_secret_value(),
                algorithm=JWT_ALGORITHM,
                headers=headers,
            )

            logger.info("🎫 Token JWT criado com sucesso")
            logger.debug(f"Token expira em: {JWT_EXPIRATION_SECONDS}s")

            return token

        except Exception as e:
            logger.error(f"🚨 Erro criando token JWT: {e}")
            raise AuthenticationError(
                "Falha ao criar token de acesso",
                details={"error": str(e)},
            ) from e

    def _save_token_to_file(self) -> None:
        """Save current token to file for external access (cloud-compatible)."""
        if not self.access_token:
            return

        try:
            with open(TOKEN_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(self.access_token)
            logger.info("🔑 ACCESS TOKEN gerado e salvo.")
        except OSError as e:
            # Expected in read-only environments like FastMCP Cloud
            logger.info("🔑 ACCESS TOKEN gerado (ambiente read-only detectado).")
            logger.debug(f"Detalhes: {e}")

    def generate_new_token(self) -> str:
        """Generate a new JWT token and update internal state."""
        if not self.key_pair:
            raise AuthenticationError("Sistema JWT não inicializado")

        try:
            # Generate new token
            self.access_token = self._create_access_token()

            # Persist for external access
            self._save_token_to_file()

            logger.info("🔄 Novo token JWT gerado com sucesso!")
            return self.access_token

        except Exception as e:
            raise TokenGenerationError(
                "Erro ao gerar novo token",
                details={"error": str(e)},
            ) from e

    def get_current_token(self) -> str:
        """Get current JWT token, generate new if needed."""
        if not self.access_token:
            return self.generate_new_token()
        return self.access_token

    def get_auth_provider(self) -> Optional[JWTVerifier]:
        """Get JWT verifier for FastMCP authentication."""
        return self.auth_provider

    def rotate_keys(self, new_private_key_pem: str) -> None:
        """Rotate keys with graceful transition and overlap period."""
        with self._lock:
            try:
                logger.info("🔄 Iniciando rotação de chaves...")

                # Store current key as previous (if exists)
                if self.key_pair:
                    self.previous_key_pair = self.key_pair
                    self.previous_kid = self.kid
                    self.rotation_timestamp = time.time()
                    logger.info("📚 Chave atual movida para previous")

                # Create new RSAKeyPair from provided PEM
                from pydantic import SecretStr

                new_key_pair = RSAKeyPair(
                    private_key=SecretStr(new_private_key_pem),
                    public_key=self._extract_public_key_from_private(
                        new_private_key_pem
                    ),
                )

                # Generate new kid
                import hashlib

                key_hash = hashlib.sha256(
                    new_key_pair.public_key.encode('utf-8')
                ).hexdigest()[:8]
                new_kid = f"key-{key_hash}"

                # Atomic swap
                self.key_pair = new_key_pair
                self.kid = new_kid

                # Invalidate current token to force regeneration with new key
                self._current_token = None
                self._token_expiry = None

                # Update main access_token
                self.access_token = self._create_access_token()
                self._save_token_to_file()

                logger.info("✅ Rotação de chaves concluída")
                logger.info("🆔 Novo Key ID: %s", self.kid)
                if self.previous_kid:
                    logger.info(
                        "📚 Previous Key ID: %s (grace period: %d min)",
                        self.previous_kid,
                        self.grace_period_seconds // 60,
                    )

            except Exception as e:
                logger.error("🚨 Erro durante rotação de chaves: %s", str(e))
                raise AuthenticationError(
                    "Falha na rotação de chaves", details={"error": str(e)}
                ) from e

    def _extract_public_key_from_private(self, private_key_pem: str) -> str:
        """Extract public key PEM from private key PEM."""
        try:
            from cryptography.hazmat.primitives import serialization

            # Load private key
            private_key_obj = serialization.load_pem_private_key(
                private_key_pem.encode(), password=None
            )

            # Extract public key
            public_key_obj = private_key_obj.public_key()
            public_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            return public_pem.decode('utf-8')

        except Exception as e:
            raise AuthenticationError(
                "Falha ao extrair chave pública", details={"error": str(e)}
            ) from e

    def cleanup_expired_keys(self) -> bool:
        """Remove expired previous keys after grace period."""
        with self._lock:
            if (
                self.previous_key_pair
                and self.rotation_timestamp
                and time.time() - self.rotation_timestamp > self.grace_period_seconds
            ):

                logger.info(
                    "🧹 Removendo chave anterior expirada (kid: %s)", self.previous_kid
                )
                self.previous_key_pair = None
                self.previous_kid = None
                self.rotation_timestamp = None
                return True
            return False

    def get_public_jwks(self) -> Dict[str, Any]:
        """Get all active public keys in JWKS format (current + previous if in grace period)."""
        try:
            keys = []

            # Always include current key
            if self.key_pair:
                current_jwk = self.get_public_jwk()
                keys.append(current_jwk)

            # Include previous key if within grace period
            if (
                self.previous_key_pair
                and self.previous_kid
                and self.rotation_timestamp
                and time.time() - self.rotation_timestamp < self.grace_period_seconds
            ):

                # Create JWK for previous key
                previous_jwk = self._create_jwk_for_key_pair(
                    self.previous_key_pair, self.previous_kid
                )
                keys.append(previous_jwk)

            return {"keys": keys}

        except Exception as e:
            logger.error("🚨 Erro gerando JWKS completo: %s", str(e))
            raise AuthenticationError(
                "Falha ao gerar JWKS", details={"error": str(e)}
            ) from e

    def _create_jwk_for_key_pair(
        self, key_pair: RSAKeyPair, kid: str
    ) -> Dict[str, Any]:
        """Create JWK object for a specific key pair and kid."""
        import base64

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Parse the public key
        public_key_obj = serialization.load_pem_public_key(key_pair.public_key.encode())

        if not isinstance(public_key_obj, rsa.RSAPublicKey):
            raise ValueError("Invalid RSA public key")

        # Get RSA public numbers
        public_numbers = public_key_obj.public_numbers()

        # Convert to JWK format
        def _int_to_base64url(value: int) -> str:
            """Convert integer to base64url-encoded string."""
            byte_length = (value.bit_length() + 7) // 8
            bytes_value = value.to_bytes(byte_length, 'big')
            return base64.urlsafe_b64encode(bytes_value).decode('utf-8').rstrip('=')

        return {
            "kty": "RSA",
            "use": "sig",
            "kid": kid,
            "alg": "RS256",
            "n": _int_to_base64url(public_numbers.n),
            "e": _int_to_base64url(public_numbers.e),
        }
