#!/usr/bin/env python3
"""Debug FastMCP Cloud JWT Authentication - RS256 inspector."""

import json

from typing import Any

import jwt

from src.config.constants import JWT_AUDIENCE
from src.config.constants import JWT_ISSUER
from src.jwt_manager import JWTManager


def inspect_jwt_manager_token() -> dict[str, Any]:
    """Gera token via JWTManager e imprime claims relevantes."""

    print("� INSPEÇÃO RS256 - FastMCP JWT via JWTManager")
    print("=" * 60)

    jwt_manager = JWTManager()
    if not jwt_manager.key_pair:
        raise RuntimeError("JWTManager não inicializou o par de chaves RSA")

    token = jwt_manager.generate_new_token()

    print("\n� TOKEN GERADO (RS256):")
    print(token)

    decoded = jwt.decode(
        token,
        jwt_manager.key_pair.public_key,
        algorithms=["RS256"],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
    )

    print("\n📋 CLAIMS DECODIFICADAS:")
    print(json.dumps(decoded, indent=2))

    print("\n🎯 VALIDAÇÕES PRINCIPAIS:")
    print(f"  - issuer: {decoded.get('iss')}")
    print(f"  - audience: {decoded.get('aud')}")
    print(f"  - scope: {decoded.get('scope')}")

    return decoded


if __name__ == "__main__":
    inspect_jwt_manager_token()
