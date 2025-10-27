#!/usr/bin/env python3
"""Script de teste simples para verificar se o servidor MCP está funcionando."""

import os
import subprocess
import sys

from pathlib import Path


def test_python_availability():
    """Testa se o Python está disponível no sistema."""
    try:
        # Tentar diferentes comandos Python
        python_commands = ['python', 'python3', 'py']

        for cmd in python_commands:
            try:
                result = subprocess.run(
                    [cmd, '--version'], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    print(f"✅ Python encontrado: {cmd}")
                    print(f"   Versão: {result.stdout.strip()}")
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        print("❌ Python não encontrado no PATH")
        return None

    except Exception as e:
        print(f"❌ Erro ao testar Python: {e}")
        return None


def test_server_file():
    """Testa se o arquivo server.py existe e é válido."""
    server_path = Path("server.py")
    if server_path.exists():
        print(f"✅ Arquivo server.py encontrado: {server_path.absolute()}")

        # Verificar se é um arquivo Python válido
        try:
            with open(server_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'import fastmcp' in content or 'from fastmcp' in content:
                    print("✅ Servidor FastMCP detectado no arquivo")
                    return True
                else:
                    print("⚠️  FastMCP não detectado no arquivo server.py")
                    return False
        except Exception as e:
            print(f"❌ Erro ao ler server.py: {e}")
            return False
    else:
        print(f"❌ Arquivo server.py não encontrado em: {server_path.absolute()}")
        return False


def test_imports():
    """Testa se as dependências necessárias estão disponíveis."""
    try:
        import fastmcp

        print("✅ FastMCP instalado e importável")
        return True
    except ImportError as e:
        print(f"❌ FastMCP não disponível: {e}")
        print("   Instale com: pip install fastmcp")
        return False


def main():
    """Função principal de teste."""
    print("🧪 TESTE DO SERVIDOR MCP TREE OF THOUGHTS")
    print("=" * 50)

    # Teste 1: Verificar Python
    python_cmd = test_python_availability()
    if not python_cmd:
        print("\n❌ IMPOSSÍVEL PROSSEGUIR: Python não disponível")
        return False

    # Teste 2: Verificar arquivo do servidor
    if not test_server_file():
        print("\n❌ IMPOSSÍVEL PROSSEGUIR: Problemas com server.py")
        return False

    # Teste 3: Verificar imports
    if not test_imports():
        print("\n❌ IMPOSSÍVEL PROSSEGUIR: Dependências não disponíveis")
        return False

    print("\n✅ TODOS OS TESTES BÁSICOS PASSARAM!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print(f"1. Execute: {python_cmd} server.py")
    print("2. Configure no Cursor como 'mcp-treeofthoughts'")
    print("3. Reinicie o Cursor para ativar o MCP")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
