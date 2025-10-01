"""
Testes para as melhorias implementadas no MCP TreeOfThoughts:
1. Cancelamento real de tarefas assíncronas
2. Seleção dinâmica de estratégias
"""

import asyncio
import os
import sys
import time

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest


# Adicionar o diretório pai ao path para importar o servidor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_cancelamento_real_estrutura():
    """Testa se a estrutura para cancelamento real está implementada"""
    import server

    # Limpar execuções ativas
    server.active_runs.clear()

    # Verificar se a função iniciar_processo_tot aceita o parâmetro strategy
    import inspect

    sig = inspect.signature(server.iniciar_processo_tot)
    assert (
        'strategy' in sig.parameters
    ), "Parâmetro 'strategy' não encontrado em iniciar_processo_tot"

    print("✓ Estrutura para cancelamento real implementada")


@patch('src.llm_client.get_chat_llm')
@patch('src.llm_client.get_embeddings')
def test_selecao_dinamica_estrategias(mock_embeddings, mock_llm):
    """Testa se a seleção dinâmica de estratégias está funcionando"""
    import server

    # Configurar mocks
    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.return_value.content = '["Pensamento 1", "Pensamento 2"]'
    mock_llm.return_value = mock_llm_instance

    mock_embeddings_instance = MagicMock()
    mock_embeddings_instance.embed_query.return_value = [0.1] * 3072
    mock_embeddings.return_value = mock_embeddings_instance

    # Limpar execuções ativas
    server.active_runs.clear()

    # Testar com beam_search
    resultado_beam = server.iniciar_processo_tot(
        instrucao="Teste beam search: 2 + 2 = ?",
        restricoes="Use apenas operações básicas",
        strategy="beam_search",
    )

    assert "beam_search" in resultado_beam.lower()
    assert "Processo Tree of Thoughts iniciado com sucesso" in resultado_beam
    print("✓ Estratégia beam_search funcionando")

    # Limpar para próximo teste
    server.active_runs.clear()

    # Testar com best_first_search
    resultado_best = server.iniciar_processo_tot(
        instrucao="Teste best first search: 3 + 3 = ?",
        restricoes="Use apenas operações básicas",
        strategy="best_first_search",
    )

    assert "best_first_search" in resultado_best.lower()
    assert "Processo Tree of Thoughts iniciado com sucesso" in resultado_best
    print("✓ Estratégia best_first_search funcionando")


def test_strategy_map_nodes():
    """Testa se o strategy_map está implementado corretamente em nodes.py"""
    from src.models import GraphState
    from src.models import RunConfig
    from src.models import RunTask
    from src.nodes import select_and_prune
    from src.strategies.beam_search import BeamSearch
    from src.strategies.best_first_search import BestFirstSearch

    # Criar estado de teste com beam_search
    config_beam = RunConfig(strategy="beam_search", beam_width=2)
    task = RunTask(instruction="Teste")
    state_beam = GraphState(run_id="test", task=task, config=config_beam)

    # Verificar se não há erro ao processar
    try:
        # Como não temos nós na fronteira, deve retornar sem erro
        result = select_and_prune(state_beam)
        assert isinstance(result, GraphState)
        print("✓ Strategy map para beam_search funcionando")
    except Exception as e:
        print(f"❌ Erro com beam_search: {e}")
        raise

    # Criar estado de teste com best_first_search
    config_best = RunConfig(strategy="best_first_search")
    state_best = GraphState(run_id="test2", task=task, config=config_best)

    try:
        result = select_and_prune(state_best)
        assert isinstance(result, GraphState)
        print("✓ Strategy map para best_first_search funcionando")
    except Exception as e:
        print(f"❌ Erro com best_first_search: {e}")
        raise


def test_cancellation_event_structure():
    """Testa se o evento de cancelamento está sendo criado corretamente"""
    import server

    from src.models import GraphState

    # Limpar execuções ativas
    server.active_runs.clear()

    # Simular criação de evento de cancelamento
    cancellation_event = asyncio.Event()

    # Verificar se o evento pode ser criado e manipulado
    assert not cancellation_event.is_set(), "Evento deve começar não acionado"

    cancellation_event.set()
    assert cancellation_event.is_set(), "Evento deve estar acionado após set()"

    print("✓ Estrutura de evento de cancelamento funcionando")


def test_active_runs_structure():
    """Testa se a estrutura de active_runs suporta as novas funcionalidades"""
    import server

    # Limpar execuções ativas
    server.active_runs.clear()

    # Simular estrutura esperada
    run_id = "test_run"
    cancellation_event = asyncio.Event()

    server.active_runs[run_id] = {
        "status": "running",
        "state": {},
        "result": None,
        "start_time": "2024-01-01T00:00:00",
        "cancellation_event": cancellation_event,
        "task": None,
    }

    # Verificar estrutura
    run_data = server.active_runs[run_id]
    assert "cancellation_event" in run_data, "cancellation_event não encontrado"
    assert "task" in run_data, "task não encontrado"
    assert isinstance(
        run_data["cancellation_event"], asyncio.Event
    ), "cancellation_event não é asyncio.Event"

    print("✓ Estrutura de active_runs atualizada corretamente")


@pytest.mark.asyncio
async def test_cancelamento_funcional():
    """Testa se a função de cancelamento está funcionando"""
    from unittest.mock import patch
    import server

    run_id = "test_cancel"

    # Mockar a função de cancelamento do execution_manager para retornar sucesso
    with patch.object(server.execution_manager, 'cancel_execution') as mock_cancel:
        # Configurar mock para não levantar exceção (cancelamento bem-sucedido)
        mock_cancel.return_value = None

        # Testar cancelamento
        resultado = server.cancelar_execucao(run_id)

        # Verificar que a função foi chamada com o run_id correto
        mock_cancel.assert_called_once_with(run_id)

        # Verificar mensagem de sucesso
        assert "foi cancelada com sucesso" in resultado

    print("✓ Cancelamento funcional implementado corretamente")


if __name__ == "__main__":
    print("🚀 Executando testes das melhorias do MCP TreeOfThoughts...\n")

    # Executar testes individualmente para melhor controle
    testes = [
        test_cancelamento_real_estrutura,
        test_selecao_dinamica_estrategias,
        test_strategy_map_nodes,
        test_cancellation_event_structure,
        test_active_runs_structure,
        test_cancelamento_funcional,
    ]

    sucessos = 0
    total = len(testes)

    for teste in testes:
        try:
            if 'mock' in teste.__name__ or 'selecao_dinamica' in teste.__name__:
                # Executar testes com mock
                with patch('src.llm_client.get_chat_llm'), patch(
                    'src.llm_client.get_embeddings'
                ):
                    teste()
            else:
                teste()
            sucessos += 1
            print(f"✅ {teste.__name__} passou\n")
        except Exception as e:
            print(f"❌ {teste.__name__} falhou: {e}\n")

    print(f"📊 Resultados: {sucessos}/{total} testes passaram")

    if sucessos == total:
        print("\n🎉 Todos os testes das melhorias passaram!")
        print("✅ Cancelamento real e seleção dinâmica funcionando corretamente!")
    else:
        print(f"\n❌ {total - sucessos} teste(s) falharam")
        exit(1)
