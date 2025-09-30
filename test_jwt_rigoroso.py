#!/usr/bin/env python3
"""Teste rigoroso do JWT Enterprise."""

import jwt

from generate_valid_jwt import EnterpriseJWTGenerator


def test_jwt_validation():
    """Executa testes rigorosos de validação JWT."""

    print("🔍 TESTE RIGOROSO JWT ENTERPRISE")
    print("=" * 50)

    # Teste 1: Geração e validação local
    generator = EnterpriseJWTGenerator()
    token, payload = generator.generate_production_token()

    print(f"📋 Token gerado: {token[:50]}...")
    print(f"🔑 Secret key: {generator.secret_key}")

    # Teste 2: Validação local
    validation = generator.validate_token(token)
    print(f"✅ Validação local: {validation['valid']}")

    if validation['valid']:
        print("🎯 Payload validado:")
        for key, value in validation['payload'].items():
            print(f"  - {key}: {value}")
    else:
        print(f"❌ Erro: {validation['error']}")

    # Teste 3: Decodificação sem validação
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        print("🔓 Decodificação sem verificação:")
        print(f"  - aud: {decoded.get('aud')}")
        print(f"  - iss: {decoded.get('iss')}")
        print(f"  - exp: {decoded.get('exp')}")
        print(f"  - iat: {decoded.get('iat')}")
    except Exception as e:
        print(f"❌ Erro na decodificação: {e}")

    # Teste 4: Verificar timestamps
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    exp_time = payload.get('exp', 0)

    print(f"⏰ Timestamp atual: {int(now)}")
    print(f"⏰ Token expira em: {exp_time}")
    print(f"⏰ Token válido por: {int((exp_time - now) / 3600)} horas")

    return token


if __name__ == "__main__":
    test_jwt_validation()
