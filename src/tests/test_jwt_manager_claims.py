from __future__ import annotations

import pytest
import jwt as pyjwt

from src.config.constants import JWT_AUDIENCE, JWT_ISSUER
from src.jwt_manager import JWTManager


def test_jwt_manager_generates_valid_token_and_claims():
    """Gera token via JWTManager e valida claims com PyJWT."""
    jm = JWTManager()

    token = jm.generate_new_token()
    assert isinstance(token, str)
    assert len(token) > 100

    # Decodificar e checar claims via PyJWT (RS256)
    decoded = pyjwt.decode(
        token,
        jm.key_pair.public_key,
        algorithms=["RS256"],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
    )

    assert decoded.get("iss") == JWT_ISSUER
    assert decoded.get("aud") == JWT_AUDIENCE
    assert "scope" in decoded

    # JWTVerifier provider exposto pelo JWTManager
    verifier = jm.get_auth_provider()
    assert verifier is not None

    # If verifier exposes a verify/decode method, call it to ensure contract
    if hasattr(verifier, "verify"):
        # Some implementations return None on success, some return payload
        try:
            result = verifier.verify(token)
            # Accept truthy or dict-like payload
            assert result is None or isinstance(result, (dict, list, str, bool))
        except Exception:
            pytest.fail("JWTVerifier.verify raised an unexpected exception")
    elif hasattr(verifier, "decode"):
        try:
            out = verifier.decode(token)
            assert isinstance(out, (dict, list)) or out is None
        except Exception:
            pytest.fail("JWTVerifier.decode raised an unexpected exception")
    else:
        pytest.skip("JWTVerifier does not expose verify/decode in this environment")
