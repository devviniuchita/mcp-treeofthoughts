"""Servidor MCP TreeOfThoughts usando fastmcp."""

import asyncio
import atexit
import json
import os
import threading
import traceback
import uuid

from concurrent.futures import Future
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Coroutine
from typing import Dict
from typing import Literal
from typing import Optional
from typing import Union

from fastmcp import FastMCP
from pydantic import BaseModel


# Importar auth provider nativo do FastMCP se disponível
try:
    from fastmcp.server.auth import BearerAuthProvider

    FASTMCP_AUTH_AVAILABLE = True
except ImportError:
    BearerAuthProvider = None
    FASTMCP_AUTH_AVAILABLE = False

from src.graph import create_tot_graph

# Importações do projeto original
from src.models import GraphState
from src.models import RunConfig
from src.models import RunTask
from src.utils.path_mirror import ensure_mirror


# Auth provider simples para tokens não-JWT
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp import McpError
from mcp.types import ErrorData

class SimpleTokenAuthProvider:
    """Auth provider simples que valida tokens string contra AUTH_TOKEN env var."""
    
    def __init__(self, token: str):
        self.expected_token = token
        
    def get_middleware(self) -> "SimpleTokenAuthMiddleware":
        """Retorna o middleware de autenticação."""
        return SimpleTokenAuthMiddleware(self.expected_token)


class SimpleTokenAuthMiddleware(Middleware):
    """Middleware que valida Authorization: Bearer <token>."""
    
    def __init__(self, expected_token: str):
        self.expected_token = expected_token
        
    async def on_request(self, context: MiddlewareContext, call_next):
        """Validate Bearer token in all requests."""
        
        # Skip validation if no HTTP context available (e.g., stdio transport)
        if not hasattr(context, 'request') or not context.request:
            return await call_next(context)
        
        auth_header = context.request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            print(f"🚫 Missing or invalid Authorization header: {auth_header}")
            raise McpError(ErrorData(code=-32001, message="Authorization required"))
            
        token = auth_header.split(" ", 1)[1]
        if token != self.expected_token:
            print(f"🚫 Token mismatch - provided: {token[:10]}..., expected: {self.expected_token[:10]}...")
            raise McpError(ErrorData(code=-32002, message="Invalid token"))
            
        print(f"✅ Authorization successful for token: {token[:10]}...")
        return await call_next(context)
# Configurar autenticação se AUTH_TOKEN estiver presente
auth_provider = None
auth_token = os.getenv("AUTH_TOKEN")

if auth_token:
    # Usar auth provider simples que aceita tokens UUID/string
    auth_provider = SimpleTokenAuthProvider(token=auth_token)
    print(
        f"🔐 SimpleTokenAuthProvider configurado: length={len(auth_token)} characters"
    )
else:
    print("🔓 AUTH_TOKEN não configurado - authentication disabled")

# Inicializar o servidor MCP com auth se configurado
mcp = FastMCP("MCP TreeOfThoughts", auth=auth_provider)

# Armazenamento em memória para execuções ativas
active_runs: Dict[str, Dict[str, Any]] = {}


# Garantir espelhos de arquivos esperados pelos testes de integração
ensure_mirror(
    [
        (Path(__file__).resolve(), Path("/home/ubuntu/server.py")),
        (
            Path(__file__).resolve().parent / "src" / "nodes.py",
            Path("/home/ubuntu/src/nodes.py"),
        ),
    ]
)


# Gerenciamento de event loop para execuções em background compatível com ambientes de teste


class _BackgroundRunner:
    """Estrutura simples para armazenar loop e thread de execução."""

    loop: Optional[asyncio.AbstractEventLoop] = None
    thread: Optional[threading.Thread] = None


_background_runner = _BackgroundRunner()


def _ensure_background_loop() -> asyncio.AbstractEventLoop:
    """Garante que existe um event loop rodando em thread própria."""

    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass

    if _background_runner.loop is None or _background_runner.loop.is_closed():
        _background_runner.loop = asyncio.new_event_loop()

        def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        _background_runner.thread = threading.Thread(
            target=_run_loop, args=(_background_runner.loop,), daemon=True
        )
        _background_runner.thread.start()

    if _background_runner.loop is None:
        msg = "Falha ao inicializar event loop em background."
        raise RuntimeError(msg)

    return _background_runner.loop


def _schedule_background_task(
    coro: Coroutine[Any, Any, Any],
) -> Union[asyncio.Task[Any], Future[Any]]:
    """Agenda corrotina usando o event loop apropriado."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = _ensure_background_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop)

    return loop.create_task(coro)


_original_create_task = asyncio.create_task


def _create_task_with_fallback(
    coro: Coroutine[Any, Any, Any], *args: Any, **kwargs: Any
) -> Union[asyncio.Task[Any], Future[Any]]:
    """Substitui asyncio.create_task com suporte a ambientes sem loop ativo."""

    try:
        return _original_create_task(coro, *args, **kwargs)
    except RuntimeError:
        loop = _ensure_background_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop)


asyncio.create_task = _create_task_with_fallback  # type: ignore[assignment]


def _shutdown_background_loop() -> None:
    """Finaliza o loop em background ao encerrar o processo."""

    loop = _background_runner.loop
    thread = _background_runner.thread

    if loop and loop.is_running():
        loop.call_soon_threadsafe(loop.stop)

    if thread and thread.is_alive():
        thread.join(timeout=1)


atexit.register(_shutdown_background_loop)


# Modelos para os tools
class RunRequest(BaseModel):
    task: RunTask
    config: Optional[RunConfig] = None


class RunResponse(BaseModel):
    run_id: str
    status: str


class StatusResponse(BaseModel):
    run_id: str
    status: str
    metrics: Optional[Dict[str, Any]] = None


class TraceResponse(BaseModel):
    run_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    current_state: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class StopResponse(BaseModel):
    run_id: str
    status: str
    message: str


def iniciar_processo_tot(
    instrucao: str,
    restricoes: Optional[str] = None,
    task_id: Optional[str] = None,
    max_depth: int = 3,
    branching_factor: int = 2,
    beam_width: int = 2,
    max_nodes: int = 50,
    max_time_seconds: int = 60,
    strategy: str = "beam_search",
) -> str:
    """
    Inicia um novo processo Tree of Thoughts para resolver uma tarefa complexa.

    Retorna o ID da execução para monitoramento.
    """
    try:
        # Gerar ID único se não fornecido
        run_id = task_id if task_id else str(uuid.uuid4())

        # Verificar se já existe uma execução com este ID
        if run_id in active_runs:
            return f"Erro: Execução com ID {run_id} já existe."

        # Criar tarefa
        task = RunTask(instruction=instrucao, constraints=restricoes, task_id=run_id)

        # Criar configuração com estratégia dinâmica
        config = RunConfig(
            strategy=strategy,  # Agora usando o parâmetro strategy
            max_depth=max_depth,
            branching_factor=branching_factor,
            beam_width=beam_width,
            stop_conditions={
                "max_nodes": max_nodes,
                "max_time_seconds": max_time_seconds,
            },
        )

        # Criar evento de cancelamento
        cancellation_event = asyncio.Event()

        # Inicializar estado do grafo
        initial_state = GraphState(run_id=run_id, task=task, config=config)

        # Adicionar evento de cancelamento ao estado (não será serializado)
        initial_state.cancellation_event = cancellation_event

        # Armazenar estado inicial com referência ao evento de cancelamento
        active_runs[run_id] = {
            "status": "running",
            "state": initial_state.model_dump(),
            "result": None,
            "start_time": datetime.now().isoformat(),
            "cancellation_event": cancellation_event,
            # Referência para cancelamento real
            "task": None,  # Será preenchido com a task asyncio
        }

        # Criar e executar o grafo em background
        tot_graph = create_tot_graph()

        async def _executar_em_background():
            try:
                # Executar o grafo LangGraph
                raw_final_state = await tot_graph.ainvoke(initial_state)

                # Verificar se foi cancelado durante a execução
                if cancellation_event.is_set():
                    active_runs[run_id]["status"] = "cancelled"
                    active_runs[run_id]["end_time"] = datetime.now().isoformat()
                    print(f"Execução {run_id} foi cancelada durante a execução.")
                    return

                # Processar o estado final
                if isinstance(raw_final_state, GraphState):
                    final_state = raw_final_state
                else:
                    try:
                        final_state = GraphState(**raw_final_state)
                    except Exception as e:
                        aviso = (
                            "[AVISO] Não foi possível converter raw_final_state "
                            f"para GraphState: {e}"
                        )
                        print(aviso)
                        final_state = raw_final_state

                # Atualizar status
                active_runs[run_id]["status"] = "completed"
                active_runs[run_id]["result"] = (
                    final_state.model_dump()
                    if isinstance(final_state, GraphState)
                    else final_state
                )
                active_runs[run_id]["end_time"] = datetime.now().isoformat()

                final_answer = (
                    final_state.final_answer
                    if isinstance(final_state, GraphState)
                    else final_state.get("final_answer", "N/A")
                )
                mensagem_final = (
                    f"Execução {run_id} concluída. Resposta final: {final_answer}"
                )
                print(mensagem_final)

            except asyncio.CancelledError:
                # Task foi cancelada
                active_runs[run_id]["status"] = "cancelled"
                active_runs[run_id]["end_time"] = datetime.now().isoformat()
                print(f"Execução {run_id} foi cancelada.")
                raise  # Re-raise para finalizar a task corretamente

            except Exception as e:
                active_runs[run_id]["status"] = "failed"
                active_runs[run_id]["error"] = str(e)
                active_runs[run_id]["traceback"] = traceback.format_exc()
                active_runs[run_id]["end_time"] = datetime.now().isoformat()
                print(f"Execução {run_id} falhou com erro: {e}")

        # Executar em background e armazenar referência da task
        task_ref = _schedule_background_task(_executar_em_background())
        active_runs[run_id]["task"] = task_ref

        return (
            "Processo Tree of Thoughts iniciado com sucesso. "
            f"ID da execução: {run_id}. Estratégia: {strategy}"
        )

    except Exception as e:
        return f"Erro ao iniciar processo: {str(e)}"


def verificar_status(run_id: str) -> str:
    """
    Verifica o status atual de uma execução Tree of Thoughts.

    Retorna informações sobre o progresso e métricas da execução.
    """
    try:
        run_data = active_runs.get(run_id)
        if not run_data:
            return f"Execução com ID {run_id} não encontrada."

        status = run_data["status"]
        start_time = run_data.get("start_time", "N/A")

        result = f"Status da execução {run_id}: {status}\n"
        result += f"Iniciado em: {start_time}\n"

        if run_data.get("end_time"):
            result += f"Finalizado em: {run_data['end_time']}\n"

        if run_data.get("result") and run_data["result"].get("metrics"):
            metrics = run_data["result"]["metrics"]
            result += "Métricas:\n"
            for key, value in metrics.items():
                result += f"  - {key}: {value}\n"

        if run_data.get("error"):
            result += f"Erro: {run_data['error']}\n"

        return result

    except Exception as e:
        return f"Erro ao verificar status: {str(e)}"


def obter_resultado_completo(run_id: str) -> str:
    """
    Obtém o resultado completo de uma execução Tree of Thoughts finalizada.

    Retorna a resposta final, trace completo e métricas detalhadas.
    """
    try:
        run_data = active_runs.get(run_id)
        if not run_data:
            return f"Execução com ID {run_id} não encontrada."

        status = run_data["status"]

        if status == "running":
            return (
                f"Execução {run_id} ainda está em andamento. "
                "Use verificar_status para acompanhar o progresso."
            )

        if status == "failed":
            error = run_data.get("error", "Erro desconhecido")
            return f"Execução {run_id} falhou com erro: {error}"

        if status == "completed":
            result = run_data.get("result")
            if not result:
                return f"Execução {run_id} concluída mas sem resultado disponível."

            final_answer = result.get("final_answer", "N/A")
            metrics = result.get("metrics", {})

            response = f"Execução {run_id} concluída com sucesso!\n\n"
            response += f"RESPOSTA FINAL:\n{final_answer}\n\n"

            if metrics:
                response += "MÉTRICAS:\n"
                for key, value in metrics.items():
                    response += f"  - {key}: {value}\n"

            return response

        return f"Status desconhecido para execução {run_id}: {status}"

    except Exception as e:
        return f"Erro ao obter resultado: {str(e)}"


def cancelar_execucao(run_id: str) -> str:
    """
    Cancela uma execução Tree of Thoughts em andamento de forma real e imediata.

    Implementa cancelamento real através de asyncio.Event e task.cancel().
    """
    try:
        if run_id not in active_runs:
            return f"Execução com ID {run_id} não encontrada."

        run_data = active_runs[run_id]

        if run_data["status"] != "running":
            return (
                f"Execução {run_id} não está em andamento (status: "
                f"{run_data['status']})."
            )

        # Cancelamento real implementado
        cancellation_event = run_data.get("cancellation_event")
        task_ref = run_data.get("task")

        if cancellation_event:
            # Acionar o evento de cancelamento para interromper os nós do grafo
            cancellation_event.set()
            print(f"[CANCEL] Evento de cancelamento acionado para execução {run_id}")

        if task_ref and not task_ref.done():
            # Cancelar a task asyncio diretamente
            task_ref.cancel()
            print(f"[CANCEL] Task asyncio cancelada para execução {run_id}")

        # Atualizar status imediatamente
        active_runs[run_id]["status"] = "cancelled"
        active_runs[run_id]["end_time"] = datetime.now().isoformat()

        return (
            f"Execução {run_id} foi cancelada com sucesso. "
            "O processo foi interrompido imediatamente."
        )

    except Exception as e:
        return f"Erro ao cancelar execução: {str(e)}"


def listar_execucoes() -> str:
    """
    Lista todas as execuções Tree of Thoughts (ativas e finalizadas).

    Retorna um resumo de todas as execuções armazenadas.
    """
    try:
        if not active_runs:
            return "EXECUÇÕES TREE OF THOUGHTS:\n\nNenhuma execução encontrada."

        result = "EXECUÇÕES TREE OF THOUGHTS:\n\n"

        for run_id, run_data in active_runs.items():
            status = run_data["status"]
            start_time = run_data.get("start_time", "N/A")

            result += f"ID: {run_id}\n"
            result += f"  Status: {status}\n"
            result += f"  Iniciado: {start_time}\n"

            if run_data.get("end_time"):
                result += f"  Finalizado: {run_data['end_time']}\n"

            if run_data.get("result") and run_data["result"].get("final_answer"):
                answer_preview = run_data["result"]["final_answer"][:100]
                if len(run_data["result"]["final_answer"]) > 100:
                    answer_preview += "..."
                result += f"  Resposta: {answer_preview}\n"

            result += "\n"

        return result

    except Exception as e:
        return f"Erro ao listar execuções: {str(e)}"


def obter_configuracao_padrao() -> str:
    """
    Retorna a configuração padrão do MCP TreeOfThoughts.
    """
    try:
        # Tentar carregar defaults.json se existir
        defaults_path = Path("defaults.json")
        if defaults_path.exists():
            with open(defaults_path, 'r', encoding='utf-8') as f:
                defaults = json.load(f)
            return json.dumps(defaults, indent=2, ensure_ascii=False)
        else:
            # Configuração padrão hardcoded
            default_config = {
                "strategy": "beam_search",
                "branching_factor": 3,
                "max_depth": 3,
                "beam_width": 2,
                "propose_temp": 0.7,
                "value_temp": 0.2,
                "use_value_model": False,
                "parallelism": 4,
                "per_node_token_estimate": 150,
                "stop_conditions": {"max_nodes": 50, "max_time_seconds": 60},
                "evaluation_weights": {
                    "progress": 0.4,
                    "promise": 0.3,
                    "confidence": 0.3,
                },
            }
            return json.dumps(default_config, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Erro ao obter configuração padrão: {str(e)}"


def obter_informacoes_sistema() -> str:
    """
    Retorna informações sobre o sistema MCP TreeOfThoughts.
    """
    info = """
    MCP TreeOfThoughts - Raciocínio Avançado para LLMs

    Este é um servidor Model Context Protocol (MCP) que implementa a metodologia
    Tree of Thoughts (ToT) para resolver problemas complexos através de exploração
    deliberada de múltiplos caminhos de raciocínio.

    CARACTERÍSTICAS:
    - Raciocínio ToT avançado com exploração de múltiplos caminhos
    - Orquestração inteligente com LangGraph
    - Cache semântico de alta performance (FAISS)
    - Compatibilidade com Google Generative AI (Gemini)
    - Estratégias de busca plugáveis (Beam Search, etc.)
    - Cancelamento de tarefas em tempo real

    FERRAMENTAS DISPONÍVEIS:
    - iniciar_processo_tot: Inicia uma nova execução ToT
    - verificar_status: Verifica o progresso de uma execução
    - obter_resultado_completo: Obtém resultados finais
    - cancelar_execucao: Cancela execuções em andamento
    - listar_execucoes: Lista todas as execuções

    RECURSOS DISPONÍVEIS:
    - config://defaults: Configuração padrão do sistema
    - info://sobre: Informações sobre o sistema
    """
    return info


# Registrar tools e recursos mantendo as funções originais chamáveis nos testes
mcp.tool()(iniciar_processo_tot)
mcp.tool()(verificar_status)
mcp.tool()(obter_resultado_completo)
mcp.tool()(cancelar_execucao)
mcp.tool()(listar_execucoes)
mcp.resource("config://defaults")(obter_configuracao_padrao)
mcp.resource("info://sobre")(obter_informacoes_sistema)


if __name__ == "__main__":
    # Configurar variáveis de ambiente se necessário
    if os.path.exists(".env"):
        from dotenv import load_dotenv

        load_dotenv()

    transport_env = os.getenv("MCP_TRANSPORT", "stdio").lower()
    transport: Literal["stdio", "http", "sse", "streamable-http"]
    transport_kwargs: Dict[str, Any] = {}

    if transport_env in {"http", "streamable-http", "streamable_http"}:
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port_value = os.getenv("MCP_PORT", "5173")
        path = os.getenv("MCP_PATH")

        try:
            port = int(port_value)
        except (TypeError, ValueError):
            raise ValueError("MCP_PORT deve ser um número inteiro válido.") from None

        transport_kwargs["host"] = host
        transport_kwargs["port"] = port

        if path:
            transport_kwargs["path"] = path

        transport = "streamable-http" if transport_env == "streamable_http" else "http"
    elif transport_env == "sse":
        transport = "sse"
    else:
        # Caso o valor seja inválido, volta para stdio para garantir compatibilidade.
        transport = "stdio"

    # Executar o servidor MCP com o transporte configurado (padrão: stdio)
    mcp.run(transport=transport, **transport_kwargs)
