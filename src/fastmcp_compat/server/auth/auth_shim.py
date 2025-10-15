"""Compatibility shim for fastmcp.server.auth classes.

Provides fallback implementations when FastMCP < 2.13 is installed.
"""

from typing import Any
from typing import Protocol

from pydantic import BaseModel


class AccessToken(BaseModel):
    """Access token model compatible with FastMCP SDK."""

    client_id: str
    scopes: list[str] = []
    extra_claims: dict[str, Any] = {}

    def __init__(self, **data):
        # Handle both dict and kwargs
        if 'scopes' in data and isinstance(data['scopes'], str):
            data['scopes'] = data['scopes'].split()
        super().__init__(**data)


class TokenVerifier(Protocol):
    """Protocol for token verifiers."""

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a bearer token and return access info if valid."""
        ...


__all__ = ["AccessToken", "TokenVerifier"]
