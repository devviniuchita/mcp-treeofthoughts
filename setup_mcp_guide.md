# 🚀 GUIA DE CONFIGURAÇÃO MCP TREE OF THOUGHTS

## 📋 Status Atual

✅ **MCP TreeOfThoughts configurado no Cursor!**
- Servidor adicionado como `mcp-treeofthoughts` no arquivo `C:\Users\ADMIN\.cursor\mcp.json`
- Configuração aponta para: `C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts\server.py`

## 🔧 Verificação do Ambiente

### 1. Verificar se Python está instalado
```bash
python --version
# ou
python3 --version
```

Se não funcionar, você precisa instalar o Python:
- Baixe de: https://python.org/downloads/
- Certifique-se de marcar "Add to PATH" durante a instalação

### 2. Instalar dependências
```bash
# Navegue até o diretório do projeto
cd "C:\Users\ADMIN\Desktop\mcp_TreeOfThoughts"

# Instalar dependências
pip install -r requirements.txt
# ou usando uv (recomendado)
uv pip install -r requirements.txt
```

### 3. Testar o servidor MCP
```bash
# Teste básico do servidor
python server.py --help

# Ou executar o servidor
python server.py
```

## 🎯 Funcionalidades Disponíveis

O servidor MCP TreeOfThoughts oferece as seguintes ferramentas:

### Ferramentas Principais:
- **`iniciar_processo_tot`** - Inicia uma nova execução Tree of Thoughts
- **`verificar_status`** - Verifica o progresso de uma execução
- **`obter_resultado_completo`** - Obtém resultados finais
- **`cancelar_execucao`** - Cancela execuções em andamento
- **`listar_execucoes`** - Lista todas as execuções

### Recursos Disponíveis:
- **`config://defaults`** - Configuração padrão do sistema
- **`info://sobre`** - Informações sobre o sistema

## 🔑 Configuração de API Keys

Para usar com Google Gemini, configure estas variáveis:

```bash
export GOOGLE_API_KEY="AIzaSyBlrQenRBgu7eHo4ZiDiNd-hSgaCWBUZ68"
export GEMINI_API_KEY="AIzaSyBlrQenRBgu7eHo4ZiDiNd-hSgaCWBUZ68"
```

## 🚨 Solução de Problemas

### Problema: "Python não encontrado"
**Solução:** Instalar Python e adicionar ao PATH

### Problema: "FastMCP não está disponível"
**Solução:**
```bash
pip install fastmcp
```

### Problema: "Não consegue conectar ao servidor"
**Solução:**
1. Verifique se o servidor está rodando: `python server.py`
2. Reinicie o Cursor completamente
3. Verifique a configuração no arquivo `.cursor\mcp.json`

## 📝 Como Usar no Cursor

1. **Reinicie o Cursor** para carregar a nova configuração MCP
2. **Digite comandos** como:
   - "Liste todas as execuções Tree of Thoughts"
   - "Inicie um processo de raciocínio avançado sobre [tópico]"
   - "Verifique o status da execução [ID]"
   - "Obtenha informações sobre o sistema"

## ✅ Próximos Passos

1. ✅ **Configuração MCP adicionada** - CONCLUÍDO
2. ⏳ **Testar ambiente Python** - Você precisa fazer
3. ⏳ **Instalar dependências** - Você precisa fazer
4. ⏳ **Reiniciar Cursor** - Você precisa fazer
5. ⏳ **Testar funcionalidades** - Você precisa fazer

## 🎉 Resultado

**O MCP TreeOfThoughts está configurado e pronto para uso!** 🎉

Uma vez que você complete os passos de instalação do Python e dependências, você poderá usar todas as funcionalidades avançadas de Tree of Thoughts diretamente no Cursor através do servidor MCP.
