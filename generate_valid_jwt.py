#!/usr/bin/env python3
"""Compat utility: gera tokens válidos reutilizando o JWTManager oficial."""

from scripts.generate_token_via_manager import get_or_create_token


def main() -> None:
    """Imprime token RS256 gerenciado pelo JWTManager."""
    token = get_or_create_token()
    print(token)


if __name__ == "__main__":
    main()
