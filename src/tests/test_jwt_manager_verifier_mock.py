from __future__ import annotations

import jwt as pyjwt

from src.config.constants import JWT_AUDIENCE
from src.config.constants import JWT_ISSUER
from src.jwt_manager import JWTManager


class MockVerifier:
    def __init__(self, public_key: str):
        self.public_key = public_key

    def verify(self, token: str):
        # Simula comportamento do JWTVerifier: decodifica e retorna payload
        return pyjwt.decode(
            token,
            self.public_key,
            algorithms=["RS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )


def test_jwt_manager_with_mocked_verifier():
    jm = JWTManager()
    token = jm.generate_new_token()

    # Injetar mock verifier que replica verificação real
    mock = MockVerifier(jm.key_pair.public_key)
    jm.auth_provider = mock

    verifier = jm.get_auth_provider()
    assert verifier is not None

    payload = verifier.verify(token)

    assert payload.get("iss") == JWT_ISSUER
    assert payload.get("aud") == JWT_AUDIENCE
    assert "scope" in payload
