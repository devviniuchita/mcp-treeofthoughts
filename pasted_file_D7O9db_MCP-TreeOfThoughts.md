# MCP - TreeOfThoughts

Este repositório contém uma implementação otimizada do MCP `TreeOfThoughts`, conforme discutido e refinado. Ele utiliza `LangGraph` para orquestração, `FAISS` para cache semântico, e uma arquitetura modular para proposição e avaliação de pensamentos.

## Estrutura do Projeto

```
/mcp-treeofthoughts
|-- api/
|   |-- server.py       # Endpoint da API (FastAPI)
|-- config/
|   |-- defaults.json   # Configuração padrão
|-- src/
|   |-- graph.py        # Definição do grafo LangGraph e estados
|   |-- models.py       # Modelos Pydantic para dados e configuração
|   |-- nodes.py        # Funções dos nós do grafo (propose, evaluate, etc.)
|   |-- prompts.py      # Templates de prompts refinados
|   |-- strategies/
|   |   |-- base.py       # Interface da estratégia de busca
|   |   |-- beam_search.py # Implementação do Beam Search
|   |-- evaluation/
|   |   |-- hybrid_evaluator.py # Módulo de avaliação híbrida
|   |-- cache/
|   |   |-- semantic_cache.py # Implementação do cache com FAISS
|-- tests/
|   |-- test_smoke_game24.py # Teste de fumaça para o Jogo de 24
|-- requirements.txt
|-- README.md
```

## Quickstart

Siga os passos abaixo para configurar e executar o MCP TreeOfThoughts:

1.  **Clone o repositório:**

    ```bash
    git clone <URL_DO_REPOSITORIO>
    cd mcp-treeofthoughts
    ```

2.  **Crie e ative um ambiente virtual:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instale as dependências:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure suas chaves de API:**

    Defina a variável de ambiente `GOOGLE_API_KEY` com sua chave de API do Google Gemini. Você pode criar um arquivo `.env` na raiz do projeto:

    ```dotenv
    GOOGLE_API_KEY="sua_chave_aqui"
    ```

    Ou exporte-a diretamente no terminal:

    ```bash
    export GOOGLE_API_KEY="sua_chave_aqui"
    ```

5.  **Execute o servidor FastAPI:**

    ```bash
    uvicorn api.server:app --reload --port 8000
    ```

    O servidor estará disponível em `http://127.0.0.1:8000`.

6.  **Envie uma requisição para iniciar um processo ToT:**

    Use `curl` ou uma ferramenta como Postman/Insomnia para enviar uma requisição `POST` para `http://127.0.0.1:8000/run`.

    **Exemplo de corpo da requisição JSON:**

    ```json
    {
      "task": {
        "instruction": "Solve the Game of 24 for the numbers 4, 6, 7, 8. You must use each number exactly once and use only the operations +, -, *, /.",
        "constraints": "Use integers only. Each number must be used exactly once. Operations allowed: +, -, *, /."
      },
      "config": {
        "max_depth": 3,
        "branching_factor": 2,
        "beam_width": 2,
        "stop_conditions": {
          "max_nodes": 50,
          "max_time_seconds": 60
        }
      }
    }
    ```

    A resposta incluirá um `run_id`.

7.  **Verifique o status e o trace da execução:**

    -   **Status:** `GET http://127.0.0.1:8000/status/{run_id}`
    -   **Trace completo (após a conclusão):** `GET http://127.0.0.1:8000/trace/{run_id}`

## Testes

Para executar os testes (atualmente apenas um teste de fumaça):

```bash
pytest tests/
```

## Contribuição

Sinta-se à vontade para contribuir com melhorias, novas estratégias de busca, avaliadores ou benchmarks. Abra uma issue ou envie um pull request.

