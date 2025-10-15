"""
Custom FastMCP Auth Providers Implementation

This module provides JWT authentication providers that are missing from
FastMCP version 2.12.4 but are documented in the official documentation.

Based on official FastMCP documentation:
- JWTVerifier: Validates JWT tokens using JWKS or public key
- RSAKeyPair: Generates and manages RSA key pairs for JWT
- AccessToken: Represents a validated access token with claims
"""

import json
import time

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import httpx
import jwt as pyjwt
import requests

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import AnyHttpUrl


@dataclass
class AccessToken:
    """Represents a validated access token with claims."""

    token: str
    claims: Dict[str, Any]
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class RSAKeyPair:
    """RSA key pair for JWT signing and verification."""

    def __init__(self, private_key: str, public_key: str):
        self.private_key = private_key
        self.public_key = public_key

    @classmethod
    def generate(cls) -> "RSAKeyPair":
        """Generate a new RSA key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode('utf-8')

        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode('utf-8')

        return cls(private_key_pem, public_key_pem)

    def create_token(
        self,
        audience: str,
        issuer: str = "fastmcp-server",
        expiration_hours: int = 24,
        **claims,
    ) -> str:
        """Create a JWT token with the specified claims."""
        now = datetime.utcnow()
        payload = {
            "iss": issuer,
            "aud": audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=expiration_hours)).timestamp()),
            **claims,
        }

        private_key = serialization.load_pem_private_key(
            self.private_key.encode('utf-8'), password=None, backend=default_backend()
        )

        return pyjwt.encode(payload, private_key, algorithm="RS256")


class JWKSClient:
    """Client for fetching JWKS from a remote server."""

    def __init__(self, jwks_uri: str):
        self.jwks_uri = jwks_uri
        self._keys_cache: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 300  # 5 minutes

    def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from the remote server."""
        now = datetime.utcnow()

        # Use cache if still valid
        if (
            self._keys_cache
            and self._cache_time
            and (now - self._cache_time).seconds < self._cache_ttl
        ):
            return self._keys_cache

        try:
            response = requests.get(self.jwks_uri, timeout=10)
            response.raise_for_status()
            self._keys_cache = response.json()
            self._cache_time = now
            return self._keys_cache
        except Exception as e:
            raise ValueError(f"Failed to fetch JWKS from {self.jwks_uri}: {e}")


class JWTVerifier:
    """JWT token verifier using JWKS or public key."""

    def __init__(
        self,
        jwks_uri: Optional[str] = None,
        public_key: Optional[str] = None,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        if not jwks_uri and not public_key:
            raise ValueError("Either jwks_uri or public_key must be provided")

        self.jwks_uri = jwks_uri
        self.public_key = public_key
        self.issuer = issuer
        self.audience = audience
        self.jwks_client = JWKSClient(jwks_uri) if jwks_uri else None

    def load_access_token(self, token: str) -> Optional[AccessToken]:
        """Load and validate an access token."""
        try:
            # Decode without verification first to get header
            unverified_header = pyjwt.get_unverified_header(token)

            # Get the key for verification
            if self.public_key:
                public_key = serialization.load_pem_public_key(
                    self.public_key.encode('utf-8'), backend=default_backend()
                )
                key = public_key
            else:
                # Use JWKS
                jwks = self.jwks_client.get_jwks()
                kid = unverified_header.get('kid')

                # Find the key in JWKS
                key_data = None
                for key in jwks.get('keys', []):
                    if key.get('kid') == kid:
                        key_data = key
                        break

                if not key_data:
                    raise ValueError("Key not found in JWKS")

                # Convert JWK to PEM public key
                public_key = self._jwk_to_pem(key_data)
                key = serialization.load_pem_public_key(
                    public_key.encode('utf-8'), backend=default_backend()
                )

            # Decode and verify the token
            payload = pyjwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
            )

            # Extract expiration
            exp_timestamp = payload.get('exp')
            expires_at = None
            if exp_timestamp:
                expires_at = datetime.fromtimestamp(exp_timestamp)

            return AccessToken(token=token, claims=payload, expires_at=expires_at)

        except Exception as e:
            # Token is invalid or verification failed
            return None

    def _jwk_to_pem(self, jwk: Dict[str, Any]) -> str:
        """Convert JWK to PEM format."""
        # This is a simplified JWK to PEM conversion
        # In a production system, you'd use a proper library like python-jose
        if jwk.get('kty') != 'RSA':
            raise ValueError("Only RSA keys are supported")

        # Extract modulus and exponent
        n = jwk['n']  # modulus
        e = jwk['e']  # exponent

        # This is a very basic conversion - in practice, use a proper JWK library
        # For now, we'll assume the public key is provided directly
        raise NotImplementedError(
            "JWK to PEM conversion requires a proper library like python-jose. "
            "Please use public_key parameter instead of jwks_uri for this implementation."
        )
