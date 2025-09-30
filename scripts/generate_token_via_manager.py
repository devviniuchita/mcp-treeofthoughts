"""Utilities para geração de JWTs RS256 reutilizando o JWTManager do projeto."""

from __future__ import annotations

from pathlib import Path

from src.config.constants import TOKEN_FILE_PATH
from src.jwt_manager import JWTManager


def get_or_create_token() -> str:
    """Recupera o token atual persistido ou gera um novo via JWTManager."""
    token_path = Path(TOKEN_FILE_PATH)

    if token_path.exists():
        existing = token_path.read_text(encoding="utf-8").strip()
        if existing:
            return existing

    manager = JWTManager()
    return manager.get_current_token()


def main() -> None:
    """Imprime um token válido gerado/persistido pelo JWTManager."""
    token = get_or_create_token()
    print(token)


if __name__ == "__main__":
    main()
