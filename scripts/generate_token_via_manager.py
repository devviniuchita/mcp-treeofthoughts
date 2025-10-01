"""Utilities para geração de JWTs RS256 reutilizando o JWTManager do projeto."""

from __future__ import annotations

from src.jwt_manager import JWTManager


def get_or_create_token() -> str:
    """Recupera o token atual persistido ou gera um novo via JWTManager."""
    # Use o JWTManager atualizado com cache thread-safe e auto-refresh
    manager = JWTManager()

    # get_or_create_token() já implementa cache inteligente e persistência
    # Não precisamos verificar TOKEN_FILE_PATH manualmente
    return manager.get_or_create_token()


def main() -> None:
    """Imprime um token válido gerado/persistido pelo JWTManager."""
    token = get_or_create_token()
    print(token)


if __name__ == "__main__":
    main()
