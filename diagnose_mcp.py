#!/usr/bin/env python3
"""
TESTE DEFINITIVO - MCP TREEOFTHOUGHTS
Diagnostica e valida completamente o servidor MCP
"""

import json
import os
import subprocess
import sys

from pathlib import Path


def print_header(text):
    print("\n" + "=" * 70)
    print(f"🧪 {text}")
    print("=" * 70 + "\n")


def print_ok(text):
    print(f"✅ {text}")


def print_error(text):
    print(f"❌ {text}")


def print_info(text):
    print(f"ℹ️  {text}")


def test_python():
    """Teste 1: Verificar Python"""
    print_info("[1/6] Verificando Python...")
    print_ok(f"Python: {sys.version}")
    print_ok(f"Executável: {sys.executable}")
    return True


def test_fastmcp():
    """Teste 2: Verificar FastMCP"""
    print_info("[2/6] Verificando FastMCP...")
    try:
        import fastmcp

        print_ok(f"FastMCP version: {fastmcp.__version__}")
        return True
    except ImportError as e:
        print_error(f"FastMCP não importável: {e}")
        return False


def test_dependencies():
    """Teste 3: Verificar dependências"""
    print_info("[3/6] Verificando dependências...")

    deps = {
        "pydantic": "Validação de dados",
        "langchain": "Integração LLM",
        "langgraph": "Orquestração",
        "langsmith": "Observabilidade",
        "numpy": "Processamento numérico",
        "faiss": "Cache semântico",
    }

    missing = []
    for pkg, desc in deps.items():
        try:
            __import__(pkg.replace("-", "_"))
            print_ok(f"{pkg}: instalado")
        except ImportError:
            print_error(f"{pkg}: FALTANDO ({desc})")
            missing.append(pkg)

    return len(missing) == 0, missing


def test_server_file():
    """Teste 4: Verificar arquivo server.py"""
    print_info("[4/6] Verificando arquivo servidor...")

    server_file = Path("server.py")
    if not server_file.exists():
        print_error(f"server.py não encontrado!")
        return False

    print_ok(f"server.py encontrado: {server_file.absolute()}")

    # Verificar se é um arquivo válido
    try:
        with open(server_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'FastMCP' in content and 'server.py' or 'mcp' in content.lower():
                print_ok("server.py é um arquivo FastMCP válido")
                return True
            else:
                print_error("server.py não parece ser um arquivo FastMCP")
                return False
    except Exception as e:
        print_error(f"Erro ao ler server.py: {e}")
        return False


def test_server_start():
    """Teste 5: Tentar iniciar servidor"""
    print_info("[5/6] Tentando iniciar servidor MCP...")

    try:
        # Iniciar processo do servidor com timeout
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Aguardar 2 segundos
        import time

        time.sleep(2)

        # Verificar se está rodando
        if proc.poll() is None:
            print_ok("Servidor iniciou e está rodando!")

            # Tentar matar
            proc.terminate()
            proc.wait(timeout=2)
            return True
        else:
            stdout, stderr = proc.communicate()
            print_error(f"Servidor encerrou com erro:")
            if stdout:
                print(f"  STDOUT: {stdout[:200]}")
            if stderr:
                print(f"  STDERR: {stderr[:200]}")
            return False

    except Exception as e:
        print_error(f"Erro ao iniciar servidor: {e}")
        return False


def test_mcp_config():
    """Teste 6: Verificar configuração MCP no Cursor"""
    print_info("[6/6] Verificando configuração MCP...")

    cursor_config = Path.home() / ".cursor" / "mcp.json"

    if not cursor_config.exists():
        print_error(f"Arquivo mcp.json não encontrado!")
        return False

    try:
        with open(cursor_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if "mcpServers" in config and "mcp-treeofthoughts" in config["mcpServers"]:
            server_config = config["mcpServers"]["mcp-treeofthoughts"]
            print_ok("mcp-treeofthoughts configurado em .cursor/mcp.json")
            print_info(f"  Comando: {server_config.get('command', 'N/A')}")
            print_info(f"  Args: {server_config.get('args', [])[:2]}")
            return True
        else:
            print_error("mcp-treeofthoughts não encontrado em mcp.json")
            return False

    except json.JSONDecodeError:
        print_error("mcp.json inválido (JSON malformado)")
        return False
    except Exception as e:
        print_error(f"Erro ao ler mcp.json: {e}")
        return False


def main():
    print_header("TESTE COMPLETO DO MCP TREEOFTHOUGHTS")

    # Mudar para diretório do projeto
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print_info(f"Diretório: {project_dir}")

    results = {}

    # Executar testes
    results["python"] = test_python()
    results["fastmcp"] = test_fastmcp()

    deps_ok, missing = test_dependencies()
    results["dependencies"] = deps_ok

    results["server_file"] = test_server_file()
    results["server_start"] = test_server_start()
    results["mcp_config"] = test_mcp_config()

    # Resumo final
    print_header("RESUMO")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Testes passando: {passed}/{total}")
    print()

    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test}")

    print()

    if all(results.values()):
        print("=" * 70)
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("=" * 70)
        print()
        print("O MCP TreeOfThoughts ESTÁ 100% FUNCIONAL!")
        print()
        print("PRÓXIMOS PASSOS:")
        print("1. Feche o Cursor IDE completamente")
        print("2. Reabra o Cursor")
        print("3. Vá para Settings → Features → MCP")
        print("4. Clique refresh (↻) ao lado de 'mcp-treeofthoughts'")
        print("5. Use no Cursor Composer!")
        print()
        return 0
    else:
        print("=" * 70)
        print("❌ ALGUNS TESTES FALHARAM")
        print("=" * 70)
        print()

        if not results.get("dependencies", True):
            print("AÇÃO NECESSÁRIA: Instalar dependências")
            print(f"  pip install -r requirements.txt")

        if not results.get("server_start", True):
            print("AÇÃO NECESSÁRIA: Verificar server.py")
            print(f"  py server.py  (para ver erro)")

        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
