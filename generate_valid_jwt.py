#!/usr/bin/env python3
"""Enterprise JWT Token Generator para FastMCP Cloud - PRODUCTION READY."""

import json
import os
import secrets

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Dict
from typing import Optional

import jwt


class EnterpriseJWTGenerator:
    """Enterprise-grade JWT generator seguindo RFC 7519 e security best practices."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.getenv(
            "MCP_AUTH_TOKEN", "mcp_treeofthoughts_2025"
        )
        self.algorithm = "HS256"

    def generate_production_token(
        self,
        subject: str = "mcp_enterprise_user",
        audience: str = "mcptreeofthoughts.fastmcp.app",
        issuer: str = "fastmcp-cloud-enterprise",
        expires_days: int = 30,
        custom_claims: Optional[Dict] = None,
    ) -> tuple[str, Dict]:
        """Gera JWT token enterprise com security compliance."""

        now = datetime.now(timezone.utc)

        # RFC 7519 compliant payload
        payload = {
            # Registered Claims (RFC 7519)
            "sub": subject,
            "aud": audience,
            "iss": issuer,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=expires_days)).timestamp()),
            "nbf": int(now.timestamp()),  # Not before
            "jti": secrets.token_urlsafe(16),  # JWT ID (unique)
            # Public Claims
            "scope": "mcp:full mcp:admin mcp:read mcp:write",
            "client_id": "mcp-treeofthoughts-enterprise",
            "token_type": "access_token",
            # Private Claims (Custom)
            "enterprise": True,
            "version": "2.0",
            "security_level": "production",
        }

        # Merge custom claims se fornecidos
        if custom_claims:
            payload.update(custom_claims)

        # Generate enterprise JWT
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return token, payload

    def validate_token(self, token: str) -> Dict:
        """Valida JWT token enterprise."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "sub"],
                },
            )
            return {"valid": True, "payload": payload}
        except jwt.PyJWTError as e:
            return {"valid": False, "error": str(e)}


def generate_jwt_token():
    """Legacy function mantida para compatibilidade."""
    generator = EnterpriseJWTGenerator()
    token, payload = generator.generate_production_token()

    print("🔐 Enterprise JWT Token Gerado (RFC 7519 Compliant):")
    print(f"Token: {token}")
    print(f"\n📋 Payload Enterprise:")
    print(json.dumps(payload, indent=2))
    print(f"\n✅ Security Features:")
    print("  - JWT ID único (jti)")
    print("  - Not Before validation (nbf)")
    print("  - Expiration validation (exp)")
    print("  - Enterprise claims")
    print("  - RFC 7519 compliant")

    return token


if __name__ == "__main__":
    token = generate_jwt_token()
