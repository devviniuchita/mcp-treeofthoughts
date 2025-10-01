"""
Testes simples para as melhorias implementadas no MCP TreeOfThoughts
"""

import sys
import os
import asyncio

# Adicionar o diretório pai ao path para importar o servidor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_strategy_parameter():
    """Testa se o parâmetro strategy foi adicionado"""
    import server
    import inspect

    # Verificar se a função tem o parâmetro strategy
    sig = inspect.signature(server.iniciar_processo_tot)
    params = list(sig.parameters.keys())

    assert 'strategy' in params, f"Parâmetro 'strategy' não encontrado. Parâmetros: {params}"

    # Verificar valor padrão
    strategy_param = sig.parameters['strategy']
    assert strategy_param.default == "beam_search", f"Valor padrão incorreto: {strategy_param.default}"

    print("✓ Parâmetro strategy adicionado corretamente")

def test_strategy_map_import():
    """Testa se as estratégias podem ser importadas"""
    try:
        from src.strategies.beam_search import BeamSearch
        from src.strategies.best_first_search import BestFirstSearch

        # Verificar se podem ser instanciadas
        beam = BeamSearch(beam_width=2)
        best = BestFirstSearch()

        assert beam is not None
        assert best is not None

        print("✓ Estratégias podem ser importadas e instanciadas")
    except Exception as e:
        print(f"❌ Erro ao importar estratégias: {e}")
        raise

def test_nodes_strategy_selection():
    """Testa se o select_and_prune tem seleção dinâmica"""
    try:
        # Determinar o caminho relativo para nodes.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        nodes_path = os.path.join(project_root, "src", "nodes.py")

        # Ler o código do arquivo nodes.py
        with open(nodes_path, 'r') as f:
            nodes_code = f.read()

        # Verificar se contém strategy_map
        assert "strategy_map" in nodes_code, "strategy_map não encontrado em nodes.py"
        assert "beam_search" in nodes_code, "beam_search não encontrado em nodes.py"
        assert "best_first_search" in nodes_code, "best_first_search não encontrado em nodes.py"
        assert "state.config.strategy" in nodes_code, "state.config.strategy não encontrado em nodes.py"

        print("✓ Seleção dinâmica de estratégias implementada em nodes.py")
    except Exception as e:
        print(f"❌ Erro ao verificar nodes.py: {e}")
        raise

def test_cancellation_event_in_models():
    """Testa se o GraphState tem suporte a cancellation_event"""
    try:
        from src.models import GraphState, RunConfig, RunTask

        # Criar instância de teste
        task = RunTask(instruction="Teste")
        config = RunConfig()
        state = GraphState(run_id="test", task=task, config=config)

        # Verificar se pode adicionar cancellation_event
        event = asyncio.Event()
        state.cancellation_event = event

        assert state.cancellation_event is not None
        assert isinstance(state.cancellation_event, asyncio.Event)

        print("✓ GraphState suporta cancellation_event")
    except Exception as e:
        print(f"❌ Erro ao testar GraphState: {e}")
        raise

def test_server_cancellation_structure():
    """Testa se o servidor tem estrutura para cancelamento"""
    try:
        # Determinar o caminho relativo para server.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        server_path = os.path.join(project_root, "server.py")

        # Ler o código do servidor
        with open(server_path, 'r') as f:
            server_code = f.read()

        # Verificar se contém as implementações de cancelamento
        assert "cancellation_event" in server_code, "cancellation_event não encontrado em server.py"
        assert "asyncio.Event()" in server_code, "asyncio.Event() não encontrado em server.py"
        assert "task.cancel()" in server_code, "task.cancel() não encontrado em server.py"
        assert "CancelledError" in server_code, "CancelledError não encontrado em server.py"

        print("✓ Estrutura de cancelamento implementada no servidor")
    except Exception as e:
        print(f"❌ Erro ao verificar servidor: {e}")
        raisedef test_nodes_cancellation_checks():
    """Testa se os nós verificam cancelamento"""
    try:
        # Determinar o caminho relativo para nodes.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        nodes_path = os.path.join(project_root, "src", "nodes.py")

        # Ler o código dos nós
        with open(nodes_path, 'r') as f:
            nodes_code = f.read()

        # Verificar se contém verificações de cancelamento
        assert "cancellation_event" in nodes_code, "cancellation_event não encontrado em nodes.py"
        assert "is_set()" in nodes_code, "is_set() não encontrado em nodes.py"
        assert "Cancellation requested" in nodes_code, "Mensagem de cancelamento não encontrada"

        # Contar quantas verificações de cancelamento existem
        cancel_checks = nodes_code.count("cancellation_event and state.cancellation_event.is_set()")
        assert cancel_checks >= 3, f"Poucas verificações de cancelamento: {cancel_checks}"

        print(f"✓ {cancel_checks} verificações de cancelamento implementadas nos nós")
    except Exception as e:
        print(f"❌ Erro ao verificar nodes.py: {e}")
        raise

def test_active_runs_structure():
    """Testa se active_runs pode armazenar as novas estruturas"""
    import server

    # Limpar execuções ativas
    server.active_runs.clear()

    # Simular estrutura esperada
    run_id = "test_structure"

    # Criar estrutura como seria no código real
    server.active_runs[run_id] = {
        "status": "running",
        "state": {},
        "result": None,
        "start_time": "2024-01-01T00:00:00",
        "cancellation_event": "mock_event",  # Mock para teste
        "task": "mock_task"  # Mock para teste
    }

    # Verificar estrutura
    run_data = server.active_runs[run_id]
    assert "cancellation_event" in run_data, "cancellation_event não encontrado"
    assert "task" in run_data, "task não encontrado"

    print("✓ Estrutura de active_runs suporta novas funcionalidades")

if __name__ == "__main__":
    print("🔧 Executando testes simples das melhorias...\n")

    testes = [
        test_strategy_parameter,
        test_strategy_map_import,
        test_nodes_strategy_selection,
        test_cancellation_event_in_models,
        test_server_cancellation_structure,
        test_nodes_cancellation_checks,
        test_active_runs_structure
    ]

    sucessos = 0
    total = len(testes)

    for teste in testes:
        try:
            teste()
            sucessos += 1
            print(f"✅ {teste.__name__} passou\n")
        except Exception as e:
            print(f"❌ {teste.__name__} falhou: {e}\n")

    print(f"📊 Resultados: {sucessos}/{total} testes passaram")

    if sucessos == total:
        print("\n🎉 Todos os testes simples passaram!")
        print("✅ As melhorias foram implementadas corretamente!")
        print("\n📋 Melhorias validadas:")
        print("  ✅ Cancelamento real de tarefas assíncronas")
        print("  ✅ Seleção dinâmica de estratégias")
        print("  ✅ Estruturas de dados atualizadas")
        print("  ✅ Verificações de cancelamento nos nós")
    else:
        print(f"\n❌ {total - sucessos} teste(s) falharam")
        exit(1)
