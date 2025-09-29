"""JWT Configuration and Token Generation following enterprise security patterns."""

import logging

from typing import Optional

from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.providers.jwt import RSAKeyPair

from .config.constants import JWT_AUDIENCE
from .config.constants import JWT_DEFAULT_SCOPES
from .config.constants import JWT_EXPIRY_SECONDS
from .config.constants import JWT_ISSUER
from .config.constants import TOKEN_FILE_PATH
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
        self._initialize_jwt_system()

    def _initialize_jwt_system(self) -> None:
        """Initialize JWT authentication system with proper error handling."""
        try:
            logger.info("🔐 Configurando autenticação JWT profissional...")

            # Generate enterprise-grade key pair
            self.key_pair = RSAKeyPair.generate()

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
            logger.info("🔑 ACCESS TOKEN gerado e salvo.")

        except Exception as e:
            logger.error(f"⚠️ Erro configurando JWT: {e}")
            raise ConfigurationError(
                "Falha na configuração do sistema JWT",
                details={"error": str(e)},
            ) from e

    def _create_access_token(self) -> str:
        """Create a new JWT access token with security standards."""
        if not self.key_pair:
            raise ConfigurationError("Key pair não configurado")

        try:
            return self.key_pair.create_token(
                subject="mcp-client",
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
                scopes=JWT_DEFAULT_SCOPES,
                expires_in_seconds=JWT_EXPIRY_SECONDS,
            )
        except Exception as e:
            raise TokenGenerationError(
                "Falha na geração do token JWT",
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
