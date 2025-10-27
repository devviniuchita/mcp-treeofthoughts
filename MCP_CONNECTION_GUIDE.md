# 🚀 GUIA COMPLETO: RESOLUÇÃO DE PROBLEMAS MCP TREEOFTHOUGHTS

## 🔍 DIAGNÓSTICO DO PROBLEMA

### Status da Configuração
✅ **MCP TreeOfThoughts CONFIGURADO no Cursor**
- Arquivo: `C:\Users\ADMIN\.cursor\mcp.json`
- Servidor: `mcp-treeofthoughts`
- Tipo de transporte: **STDIO** (recomendado)
- Wrapper: PowerShell com detecção automática de Python

---

## 🛠️ CAUSAS COMUNS E SOLUÇÕES

### PROBLEMA 1: "Server did not connect"

**Causa mais comum**: Python não está no PATH do sistema

#### Solução A: Instalar Python (RECOMENDADO)
```bash
# Baixar Python 3.13 de: https://www.python.org/downloads
# IMPORTANTE: Marcar "Add Python to PATH" durante instalação
```

#### Solução B: Usar o wrapper PowerShell (AUTOMÁTICO)
O arquivo `run_mcp_server.ps1` detecta Python automaticamente:
- Procura em `python`, `python3`, `py`
- Procura em caminhos comuns no Windows
- Define variáveis de ambiente automaticamente

#### Solução C: Usar Bash/Git Bash
O arquivo `run_mcp_server.sh` também funciona com Git Bash

---

### PROBLEMA 2: "FastMCP não está disponível"

**Solução**: Instalar dependências
```bash
cd C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts
pip install -r requirements.txt
# ou
uv pip install -r requirements.txt
```

---

### PROBLEMA 3: "Arquivo server.py não encontrado"

**Verificar**: O arquivo existe em `C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts\server.py`
```bash
dir C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts\server.py
```

---

## ✅ PASSO A PASSO: CONFIGURAÇÃO FUNCIONANDO

### Passo 1: Verificar Python
```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts\run_mcp_server.ps1"
```

**Resultado esperado:**
```
✅ Python encontrado: python (ou caminho completo)
✅ Arquivo do servidor encontrado: C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts\server.py
🚀 Iniciando servidor MCP TreeOfThoughts...
```

### Passo 2: Instalar Dependências
```powershell
cd C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts
pip install fastmcp pydantic
# ou
uv pip install fastmcp pydantic
```

### Passo 3: Testar Servidor Localmente
```powershell
python C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts\server.py
```

**Resultado esperado:** Servidor inicia sem erros e aguarda conexões

### Passo 4: Reiniciar Cursor IDE
1. Fechar o Cursor completamente
2. Aguardar 5 segundos
3. Reabrir Cursor
4. Ir para: Settings → Features → MCP
5. Verificar se `mcp-treeofthoughts` está na lista
6. Clicar no botão de refresh (↻) ao lado do servidor

### Passo 5: Usar o MCP no Cursor
No Cursor Composer, diga algo como:
- "Use o MCP TreeOfThoughts para analisar [tópico]"
- "Execute um processo Tree of Thoughts"
- "Mostre os recursos disponíveis"

---

## 🔧 CONFIGURAÇÃO MCP.JSON

**Local**: `C:\Users\ADMIN\.cursor\mcp.json`

```json
"mcp-treeofthoughts": {
  "command": "powershell",
  "args": [
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "C:\\Users\\ADMIN\\Desktop\\mcp_TreeOfThoughts\\run_mcp_server.ps1"
  ],
  "env": {
    "GOOGLE_API_KEY": "AIzaSyBlrQenRBgu7eHo4ZiDiNd-hSgaCWBUZ68",
    "GEMINI_API_KEY": "AIzaSyBlrQenRBgu7eHo4ZiDiNd-hSgaCWBUZ68",
    "LANG_SMITH_API_KEY": "lsv2_pt_8e3a7d3e3d5b4c3d8e8a7d3e3d5b4c3d_8e3a7d"
  },
  "cwd": "C:\\Users\\ADMIN\\Desktop\\mcp_TreeOfThoughts"
}
```

---

## 📊 FERRAMENTAS DISPONÍVEIS DO MCP

### Ferramentas principais:
- ✅ `iniciar_processo_tot` - Inicia execução Tree of Thoughts
- ✅ `verificar_status` - Verifica progresso
- ✅ `obter_resultado_completo` - Obtém resultados
- ✅ `cancelar_execucao` - Cancela tarefas
- ✅ `listar_execucoes` - Lista todas as execuções

### Recursos:
- ✅ `config://defaults` - Configuração padrão
- ✅ `info://sobre` - Informações do sistema

---

## 🚨 DEBUG AVANÇADO

### Verificar Logs do Cursor
1. Ir para: `Help → Developer Tools`
2. Procurar por erro relacionado a `mcp-treeofthoughts`
3. Copiar mensagem de erro completa

### Executar Teste Manual
```powershell
# Terminal PowerShell no projeto
cd C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts

# Teste 1: Verificar Python
python --version

# Teste 2: Verificar FastMCP
python -c "import fastmcp; print('✅ FastMCP OK')"

# Teste 3: Executar servidor
python server.py
```

### Usar MCP Inspector
```bash
# Instalar inspector (se não tiver)
npm install -g @modelcontextprotocol/inspector

# Executar com seu servidor
npx @modelcontextprotocol/inspector powershell -ExecutionPolicy Bypass -File "C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts\run_mcp_server.ps1"
```

---

## 📝 CHECKLIST FINAL

- [ ] Python 3.10+ instalado e no PATH
- [ ] `pip install -r requirements.txt` executado
- [ ] Arquivo `server.py` existe e é válido
- [ ] `run_mcp_server.ps1` é executável
- [ ] `mcp.json` contém configuração correta
- [ ] Cursor IDE reiniciado
- [ ] MCP `mcp-treeofthoughts` visível nas configurações
- [ ] Botão de refresh (↻) apertado no MCP
- [ ] Sem erros nos logs do Cursor (Developer Tools)

---

## 🎉 SUCESSO!

Se todos os passos acima foram seguidos e você não recebe erros, o **MCP TreeOfThoughts está 100% funcional** e pronto para uso no Cursor! 🎉

### Próximos passos:
1. Use o MCP nos seus prompts
2. Experimente funcionalidades de Tree of Thoughts
3. Integre com seus workflows de IA

---

**Última atualização**: Dezembro 2025
**Status**: ✅ ATIVO E FUNCIONAL
**Suporte**: Veja os logs do Cursor em Help → Developer Tools
