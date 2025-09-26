# Documento de Funcionamento do MCP TreeOfThoughts

## 1. Introdução

Este documento detalha o funcionamento interno do **MCP TreeOfThoughts**, uma implementação da metodologia Tree of Thoughts (ToT) que utiliza `LangGraph` para orquestração, `FAISS` para cache semântico e uma arquitetura modular para a exploração e avaliação de pensamentos. O objetivo é fornecer uma visão clara de como os componentes interagem para resolver problemas complexos.

## 2. Fluxo de Execução do Grafo

O coração do MCP é um grafo de estados gerenciado pelo `LangGraph`, definido em `src/graph.py`. O fluxo de execução segue uma série de nós, cada um responsável por uma etapa específica do processo ToT. O estado do grafo, representado pela classe `GraphState` (`src/models.py`), é passado e modificado a cada etapa.

O fluxo principal é o seguinte:

`initialize` -> `propose` -> `evaluate` -> `select` -> `check_stop_condition`

- Se `check_stop_condition` retornar `"continue"`, o ciclo volta para `propose`.
- Se `check_stop_condition` retornar `"finalize"`, o fluxo segue para o nó `finalize`.

### 2.1. `initialize_graph` (Nó de Inicialização)

- **Arquivo**: `src/nodes.py`
- **Função**: `initialize_graph(state: GraphState) -> GraphState`

**Responsabilidades:**

1.  **Criação do Nó Raiz**: Um `Node` inicial é criado com base na instrução da tarefa (`state.task.instruction`). Este nó serve como o ponto de partida da árvore de pensamentos.
2.  **Inicialização do Estado**: O `GraphState` é populado com informações iniciais:
    *   O nó raiz é adicionado ao dicionário `state.nodes`.
    *   A `state.frontier` (fronteira de exploração) é inicializada com o ID do nó raiz.
    *   O `state.best_node_id` é definido como o nó raiz.
    *   O `state.start_time` é registrado.
3.  **Inicialização do Cache Semântico**: Uma instância do `SemanticCache` (`src/cache/semantic_cache.py`) é criada e armazenada em `state.semantic_cache`. A configuração do cache (modelo de embedding, dimensão) é obtida de `state.config`.
4.  **Inicialização do Evento de Cancelamento**: Um `asyncio.Event` é criado e armazenado em `state.cancellation_event` para permitir o cancelamento da tarefa.

### 2.2. `propose_thoughts` (Nó de Proposição)

- **Arquivo**: `src/nodes.py`
- **Função**: `propose_thoughts(state: GraphState) -> GraphState`

**Responsabilidades:**

1.  **Expansão da Fronteira**: Para cada nó na `state.frontier`, esta função gera um conjunto de novos pensamentos (nós filhos).
2.  **Consulta ao Cache Semântico**: Antes de invocar o LLM, uma busca é realizada no `SemanticCache`.
    *   Uma *query* de texto é construída a partir do caminho do pensamento atual (ex: `"propose thoughts for path: ..."`).
    *   O embedding desta query é usado para buscar no índice FAISS por pensamentos semanticamente similares que já foram gerados.
    *   Se um resultado relevante for encontrado (`CACHE HIT`), os candidatos a pensamentos são recuperados do cache, evitando uma chamada custosa ao LLM.
3.  **Geração de Pensamentos com LLM (`CACHE MISS`)**: Se o cache não retornar resultados, um LLM é invocado:
    *   O cliente LLM é instanciado dinamicamente usando `get_chat_llm` com a configuração de `state.config` (modelo, temperatura).
    *   Um prompt (`PROPOSE_PROMPT`) é formatado com a instrução da tarefa, o histórico do pensamento atual e o número de candidatos a gerar (`branching_factor`).
    *   A saída do LLM é parseada de forma robusta, utilizando `with_structured_output` para esperar uma lista de strings JSON. Um mecanismo de fallback para parsing manual e divisão por linhas garante a resiliência.
4.  **Atualização do Cache**: Os novos pensamentos gerados são adicionados ao `SemanticCache` para futuras consultas.
5.  **Criação de Novos Nós**: Para cada pensamento gerado, um novo objeto `Node` é criado, ligado ao seu nó pai, e adicionado ao `state.nodes`.
6.  **Atualização da Fronteira**: A `state.frontier` é substituída pela lista de IDs dos novos nós gerados, que serão o input para a próxima etapa de avaliação.

### 2.3. `evaluate_thoughts` (Nó de Avaliação)

- **Arquivo**: `src/nodes.py`
- **Função**: `evaluate_thoughts(state: GraphState) -> GraphState`

**Responsabilidades:**

1.  **Avaliação dos Nós da Fronteira**: Cada nó na `state.frontier` (recém-gerado) é avaliado para determinar sua qualidade.
2.  **Consulta ao Cache Semântico**: Similar ao nó de proposição, o cache é consultado primeiro para verificar se uma avaliação para um caminho de pensamento semanticamente similar já existe.
3.  **Avaliação Híbrida (`CACHE MISS`)**: Se não houver cache, o `HybridEvaluator` (`src/evaluation/hybrid_evaluator.py`) é utilizado:
    *   **Heurísticas**: Regras rápidas e baratas são aplicadas primeiro (ex: penalizar pensamentos muito curtos ou longos). Se uma heurística se aplica, a avaliação do LLM é pulada.
    *   **Avaliação por LLM**: Se nenhuma heurística se aplica, um LLM é invocado com o `VALUE_PROMPT`. O LLM retorna um score multidimensional (`progress`, `promise`, `confidence`) e uma justificativa.
    *   **Cálculo do Score Final**: Um score final ponderado é calculado com base nos pesos definidos em `state.config.evaluation_weights`.
4.  **Atualização do Cache**: O resultado da avaliação (score e scores brutos) é armazenado no `SemanticCache`.
5.  **Atualização dos Nós**: O `score` e `raw_scores` de cada nó são atualizados no `state.nodes`.
6.  **Ordenação da Fronteira**: Ao final, a `state.frontier` é ordenada com base no score dos nós avaliados, do maior para o menor.

### 2.4. `select_and_prune` (Nó de Seleção e Poda)

- **Arquivo**: `src/nodes.py`
- **Função**: `select_and_prune(state: GraphState) -> GraphState`

**Responsabilidades:**

1.  **Seleção Dinâmica da Estratégia**: A estratégia de busca é instanciada dinamicamente com base no valor de `state.config.strategy`.
    *   Um `strategy_map` mapeia strings (ex: `"beam_search"`) para as classes de estratégia correspondentes (`BeamSearch`).
2.  **Aplicação da Estratégia**: A instância da estratégia de busca (ex: `BeamSearch`) é responsável por decidir quais caminhos de pensamento manter e quais descartar (podar).
    *   A função `strategy.update_frontier` é chamada, recebendo o estado atual e os nós avaliados.
    *   No caso do `BeamSearch`, ela mantém apenas os `beam_width` melhores caminhos, efetivamente podando os ramos menos promissores e atualizando a `state.frontier` para o próximo ciclo de proposição.
3.  **Atualização do Melhor Nó**: A estratégia também identifica o melhor nó global encontrado até o momento, e o `state.best_node_id` é atualizado se um novo melhor nó for encontrado.

### 2.5. `check_stop_condition` (Nó de Condição de Parada)

- **Arquivo**: `src/nodes.py`
- **Função**: `check_stop_condition(state: GraphState) -> str`

**Responsabilidades:**

- **Verificação de Múltiplas Condições**: Este nó verifica uma série de condições para decidir se o processo de exploração deve continuar ou parar. A primeira condição a ser atendida aciona a parada.
    1.  **Cancelamento Solicitado**: Verifica se o `state.cancellation_event` foi acionado.
    2.  **Número Máximo de Nós**: Compara `state.nodes_expanded` com `config.stop_conditions["max_nodes"]`.
    3.  **Tempo Máximo Decorrido**: Compara o tempo atual com `state.start_time` e `config.stop_conditions["max_time_seconds"]`.
    4.  **Solução Encontrada**: Verifica se o score do `state.best_node_id` atingiu um limiar de alta confiança (ex: >= 9.5).
    5.  **Fronteira Vazia**: Verifica se a `state.frontier` está vazia, indicando que não há mais caminhos a explorar.
    6.  **Profundidade Máxima Atingida**: Verifica se todos os nós na fronteira atingiram a `max_depth`.
- **Roteamento**: Retorna a string `"finalize"` se qualquer condição de parada for atendida, ou `"continue"` caso contrário, direcionando o fluxo do grafo.

### 2.6. `finalize_solution` (Nó de Finalização)

- **Arquivo**: `src/nodes.py`
- **Função**: `finalize_solution(state: GraphState) -> GraphState`

**Responsabilidades:**

1.  **Identificação do Melhor Caminho**: Recupera o melhor nó (`best_node`) com base no `state.best_node_id`.
2.  **Geração da Resposta Final**: Invoca um LLM com o `FINALIZE_PROMPT`, que recebe o caminho de pensamento completo do melhor nó (`best_node.path_string(state.nodes)`).
    *   O LLM é instruído a sintetizar o caminho de pensamento em uma resposta final, concisa e clara.
3.  **Armazenamento da Resposta**: A resposta gerada pelo LLM é armazenada em `state.final_answer`.
4.  **Registro de Métricas**: Popula o `state.metrics` com estatísticas finais da execução, como `nodes_expanded`, `final_score`, `time_taken` e `stop_reason`.

## 3. Interação com o Servidor MCP (fastmcp)

- **Arquivo**: `server.py`

O servidor `fastmcp` atua como a interface externa para o MCP, expondo as funcionalidades como *tools* e *resources* nativos do protocolo.

- **`iniciar_processo_tot` (Tool)**: Recebe os parâmetros da tarefa e configuração, cria o `GraphState` inicial, armazena o objeto de estado em `active_runs`, e inicia a execução do grafo em uma tarefa de background assíncrona.
- **`verificar_status` (Tool)**: Retorna o status atual (`running`, `completed`, `failed`, `cancelled`) de uma execução com base no `run_id`.
- **`obter_resultado_completo` (Tool)**: Retorna o estado final completo de uma execução concluída, incluindo a resposta final e as métricas.
- **`cancelar_execucao` (Tool)**: Acessa o objeto de estado da execução em `active_runs` e marca seu status como `cancelled`, sinalizando para o processo em background que a execução deve ser interrompida (o cancelamento pode não ser imediato).
- **`listar_execucoes` (Tool)**: Retorna um resumo de todas as execuções ativas e finalizadas armazenadas em memória.
- **`config://defaults` (Resource)**: Retorna a configuração padrão do sistema, carregada de `defaults.json` ou hardcoded.
- **`info://sobre` (Resource)**: Retorna informações gerais sobre o servidor MCP TreeOfThoughts.

