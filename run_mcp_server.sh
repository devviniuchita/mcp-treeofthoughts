#!/bin/bash
# MCP TreeOfThoughts Wrapper - Compatível com Git Bash e PowerShell

# Definir diretório do projeto
PROJECT_DIR="C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts"
SERVER_FILE="$PROJECT_DIR\server.py"

# Tentar encontrar Python em vários locais
find_python() {
    # Tentar em ordem de preferência
    for python_cmd in python python3 py; do
        if command -v "$python_cmd" &> /dev/null; then
            echo "$python_cmd"
            return 0
        fi
    done

    # Se não encontrar, tentar caminhos comuns no Windows
    if [ -f "C:\Python313\python.exe" ]; then
        echo "C:\Python313\python.exe"
        return 0
    fi

    if [ -f "C:\Program Files\Python313\python.exe" ]; then
        echo "C:\Program Files\Python313\python.exe"
        return 0
    fi

    echo "ERRO: Python não encontrado!" >&2
    return 1
}

# Encontrar Python
PYTHON_CMD=$(find_python)
if [ $? -ne 0 ]; then
    exit 1
fi

# Configurar variáveis de ambiente
export GOOGLE_API_KEY="AIzaSyBlrQenRBgu7eHo4ZiDiNd-hSgaCWBUZ68"
export GEMINI_API_KEY="AIzaSyBlrQenRBgu7eHo4ZiDiNd-hSgaCWBUZ68"
export LANG_SMITH_API_KEY="lsv2_pt_8e3a7d3e3d5b4c3d8e8a7d3e3d5b4c3d_8e3a7d"

# Executar o servidor
cd "$PROJECT_DIR"
"$PYTHON_CMD" "$SERVER_FILE"
