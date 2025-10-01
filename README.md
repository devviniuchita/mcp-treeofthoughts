# 🚀 MCP TreeOfThoughts: Raciocínio Avançado para LLMs

## ✨ Visão Geral

Bem-vindo ao **MCP TreeOfThoughts**, um **Model Context Protocol (MCP)** inovador que eleva as capacidades de resolução de problemas de Large Language Models (LLMs) através da metodologia **Tree of Thoughts (ToT)**. Inspirado na forma como os humanos pensam, este projeto permite que os LLMs explorem múltiplos caminhos de raciocínio em paralelo, avaliem o progresso e tomem decisões estratégicas para encontrar as melhores soluções.

Imagine um LLM que não apenas gera respostas, mas que delibera, planeja e refina suas ideias, como um comitê de especialistas. É exatamente isso que o TreeOfThoughts oferece: um raciocínio mais profundo, robusto e confiável para tarefas complexas.

## 🌟 Principais Destaques

- **Raciocínio ToT Avançado**: Implementação robusta da metodologia Tree of Thoughts para exploração deliberada de pensamentos.
- **Orquestração Inteligente com LangGraph**: Gerenciamento dinâmico do fluxo de raciocínio através de um grafo de estados flexível.
- **Cache Semântico de Alta Performance (FAISS)**: Otimização de custos e tempo, evitando recalcular pensamentos e avaliações já processadas ou semanticamente similares.
- **Compatibilidade Total com Google Generative AI**: Integração nativa com os modelos Gemini para geração e avaliação de pensamentos.
- **API RESTful Robusta (FastAPI)**: Interface moderna e escalável para interagir com o protocolo, com endpoints para iniciar, monitorar e cancelar execuções.
- **Estratégias de Busca Plugáveis**: Suporte para diferentes algoritmos de busca (ex: Beam Search, Best-First Search), permitindo flexibilidade na exploração do espaço de pensamentos.
- **Cancelamento de Tarefas**: Capacidade de interromper execuções em andamento, proporcionando maior controle.
- **Modelagem de Dados Segura (Pydantic V2)**: Garante a integridade e validação dos dados em todas as camadas da aplicação.

## 🛠️ Começando (Quickstart)

Siga estes passos simples para colocar o MCP TreeOfThoughts em funcionamento no seu ambiente local ou produção.

### Pré-requisitos

- Python 3.9+
- `pip` (gerenciador de pacotes Python)
- Docker (para deployment em container)
- Kubernetes (para deployment em produção)

### 🏠 Desenvolvimento Local

#### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/mcp-treeofthoughts.git # Substitua pela URL real do seu repositório
cd mcp-treeofthoughts
```

#### 2. Configure seu Ambiente Virtual

É altamente recomendável usar um ambiente virtual para gerenciar as dependências.

```bash
python -m venv venv
source venv/bin/activate  # No Linux/macOS
# venv\Scripts\activate  # No Windows
```

#### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure suas Chaves de API

Crie um arquivo `.env` na raiz do projeto com suas chaves de API do Google Gemini e LangSmith (opcional para tracing):

```dotenv
GOOGLE_API_KEY="sua_chave_api_do_google"
LANG_SMITH_API_KEY="sua_chave_api_do_langsmith" # Opcional, para tracing com LangSmith
```

### 5. Inicie o Servidor FastAPI

Execute o servidor a partir do diretório `mcp-treeofthoughts`:

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

O servidor estará acessível em `http://0.0.0.0:8000`. Você pode acessar a documentação interativa da API em `http://0.0.0.0:8000/docs`.

## 🚀 Uso da API

### `POST /run` - Iniciar uma Nova Execução ToT

Inicia um novo processo Tree of Thoughts com uma tarefa e configuração específicas.

- **Exemplo de Requisição:**

  ```json
  {
    "task": {
      "instruction": "Use os números 4, 6, 7, 8 para fazer 24. Você pode usar +, -, *, / e parênteses.",
      "constraints": "Apenas uma solução é necessária. A solução deve ser uma expressão matemática válida."
    },
    "config": {
      "strategy": "beam_search",
      "max_depth": 3,
      "beam_width": 2,
      "propose_model": "gemini-pro",
      "value_model": "gemini-pro",
      "finalize_model": "gemini-pro",
      "embedding_model": "gemini-embedding-001",
      "embedding_dim": 768,
      "propose_temp": 0.7,
      "value_temp": 0.2,
      "finalize_temp": 0.0,
      "stop_conditions": { "max_nodes": 50, "max_time_seconds": 60 }
    }
  }
  ```

- **Exemplo de Resposta:**

  ```json
  {
    "run_id": "0bc37d67-60d2-4470-aa36-16d817961d20",
    "status": "started"
  }
  ```

### `GET /status/{run_id}` - Obter Status da Execução

Verifica o status atual de uma execução ToT em andamento ou concluída.

- **Exemplo de Resposta:**

  ```json
  {
    "run_id": "0bc37d67-60d2-4470-aa36-16d817961d20",
    "status": "completed",
    "metrics": {
      "nodes_expanded": 15,
      "final_score": 9.8,
      "time_taken": 45.12,
      "stop_reason": "High score achieved"
    }
  }
  ```

### `GET /trace/{run_id}` - Obter Trace Completo

Recupera o estado final completo de uma execução, incluindo a resposta final, todos os nós explorados e métricas detalhadas.

### `POST /stop/{run_id}` - Cancelar Execução

Solicita o cancelamento de uma execução ToT em andamento.

- **Exemplo de Resposta:**

  ```json
  {
    "run_id": "0bc37d67-60d2-4470-aa36-16d817961d20",
    "status": "cancellation_requested",
    "message": "Cancellation requested. Task will stop at the next check point."
  }
  ```

### 🐳 Deployment com Docker

```bash
# Build da imagem
docker build -t mcp-treeofthoughts:latest .

# Executar container
docker run -d \
  --name mcp-treeofthoughts \
  -p 5173:5173 \
  -e GOOGLE_API_KEY=sua_chave_aqui \
  -v $(pwd)/data:/data \
  mcp-treeofthoughts:latest
```

### ☸️ Deployment Kubernetes (Produção)

Para deployments de produção, utilize os manifests Kubernetes incluídos:

```bash
# Deploy automatizado
cd k8s
./deploy.sh --domain mcp-api.suaempresa.com --image mcp-treeofthoughts:v1.0.0

# Deploy manual
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/statefulset.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/network.yaml
```

#### 🔐 Funcionalidades de Produção

- **Autenticação JWT RS256**: Tokens seguros com rotação automática de chaves
- **Endpoint JWKS**: `/.well-known/jwks.json` para validação distribuída
- **Auto-scaling**: HPA baseado em CPU/memória
- **Monitoramento**: Métricas Prometheus e alertas
- **Alta Disponibilidade**: StatefulSet com PersistentVolumes
- **Rede Segura**: NetworkPolicies e Ingress com TLS

Consulte o [Guia de Deployment Kubernetes](k8s/README.md) para instruções detalhadas.

## 🧪 Testes

Para garantir a robustez do sistema, execute os testes automatizados. Certifique-se de que o servidor FastAPI esteja **parado** ou configurado para uma porta diferente para evitar conflitos.

```bash
# Testes locais
pytest src/tests/ -v

# Testes E2E (CI/CD)
python validation_server.py &
curl http://localhost:5173/.well-known/jwks.json
curl http://localhost:5173/health
```

## 📚 Documentação Detalhada

Para uma compreensão aprofundada do projeto, consulte os seguintes documentos:

- **[ARQUITETURA.md](ARQUITETURA.md)**: Detalhes conceituais, arquitetura de software, pilha de tecnologias e diagramas.
- **[FUNCIONAMENTO.md](FUNCIONAMENTO.md)**: Explicação passo a passo do fluxo de execução do grafo e o papel de cada nó.

## 🤝 Contribuição

Contribuições são muito bem-vindas! Se você tiver ideias para melhorias, novas estratégias de busca, avaliadores ou benchmarks, sinta-se à vontade para abrir uma _issue_ ou enviar um _Pull Request_. Por favor, siga as boas práticas de desenvolvimento e os padrões de código existentes.

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
