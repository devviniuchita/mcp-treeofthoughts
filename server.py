"""
MCP TreeOfThoughts Server
Implementação de um servidor MCP usando fastmcp para raciocínio avançado com Tree of Thoughts
"""

import asyncio
import uuid
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Importações do projeto original
from src.models import RunConfig, RunTask, GraphState
from src.graph import create_tot_graph

# Inicializar o servidor MCP
mcp = FastMCP("MCP TreeOfThoughts")

# Armazenamento em memória para execuções ativas
active_runs: Dict[str, Dict[str, Any]] = {}

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

@mcp.tool()
def iniciar_processo_tot(
    instrucao: str = Field(description="Instrução da tarefa a ser resolvida"),
    restricoes: Optional[str] = Field(default=None, description="Restrições ou limitações da tarefa"),
    task_id: Optional[str] = Field(default=None, description="ID personalizado para a tarefa"),
    max_depth: int = Field(default=3, description="Profundidade máxima da árvore de pensamentos"),
    branching_factor: int = Field(default=2, description="Número de pensamentos a gerar por nó"),
    beam_width: int = Field(default=2, description="Largura do beam search"),
    max_nodes: int = Field(default=50, description="Número máximo de nós a expandir"),
    max_time_seconds: int = Field(default=60, description="Tempo máximo de execução em segundos"),
    strategy: str = Field(default="beam_search", description="Estratégia de busca: 'beam_search' ou 'best_first_search'")
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
        task = RunTask(
            instruction=instrucao,
            constraints=restricoes,
            task_id=run_id
        )
        
        # Criar configuração com estratégia dinâmica
        config = RunConfig(
            strategy=strategy,  # Agora usando o parâmetro strategy
            max_depth=max_depth,
            branching_factor=branching_factor,
            beam_width=beam_width,
            stop_conditions={
                "max_nodes": max_nodes,
                "max_time_seconds": max_time_seconds
            }
        )
        
        # Criar evento de cancelamento
        cancellation_event = asyncio.Event()
        
        # Inicializar estado do grafo
        initial_state = GraphState(
            run_id=run_id,
            task=task,
            config=config
        )
        
        # Adicionar evento de cancelamento ao estado (não será serializado)
        initial_state.cancellation_event = cancellation_event
        
        # Armazenar estado inicial com referência ao evento de cancelamento
        active_runs[run_id] = {
            "status": "running",
            "state": initial_state.model_dump(),
            "result": None,
            "start_time": datetime.now().isoformat(),
            "cancellation_event": cancellation_event,  # Referência para cancelamento real
            "task": None  # Será preenchido com a task asyncio
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
                        print(f"[AVISO] Não foi possível converter raw_final_state para GraphState: {e}")
                        final_state = raw_final_state
                
                # Atualizar status
                active_runs[run_id]["status"] = "completed"
                active_runs[run_id]["result"] = final_state.model_dump() if isinstance(final_state, GraphState) else final_state
                active_runs[run_id]["end_time"] = datetime.now().isoformat()
                
                final_answer = final_state.final_answer if isinstance(final_state, GraphState) else final_state.get("final_answer", "N/A")
                print(f"Execução {run_id} concluída. Resposta final: {final_answer}")
                
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
        task_ref = asyncio.create_task(_executar_em_background())
        active_runs[run_id]["task"] = task_ref
        
        return f"Processo Tree of Thoughts iniciado com sucesso. ID da execução: {run_id}. Estratégia: {strategy}"
        
    except Exception as e:
        return f"Erro ao iniciar processo: {str(e)}"

@mcp.tool()
def verificar_status(run_id: str = Field(description="ID da execução a verificar")) -> str:
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
            result += f"Métricas:\n"
            for key, value in metrics.items():
                result += f"  - {key}: {value}\n"
        
        if run_data.get("error"):
            result += f"Erro: {run_data['error']}\n"
        
        return result
        
    except Exception as e:
        return f"Erro ao verificar status: {str(e)}"

@mcp.tool()
def obter_resultado_completo(run_id: str = Field(description="ID da execução")) -> str:
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
            return f"Execução {run_id} ainda está em andamento. Use verificar_status para acompanhar o progresso."
        
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

@mcp.tool()
def cancelar_execucao(run_id: str = Field(description="ID da execução a cancelar")) -> str:
    """
    Cancela uma execução Tree of Thoughts em andamento de forma real e imediata.
    
    Implementa cancelamento real através de asyncio.Event e task.cancel().
    """
    try:
        if run_id not in active_runs:
            return f"Execução com ID {run_id} não encontrada."
        
        run_data = active_runs[run_id]
        
        if run_data["status"] != "running":
            return f"Execução {run_id} não está em andamento (status: {run_data['status']})."
        
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
        
        return f"Execução {run_id} foi cancelada com sucesso. O processo foi interrompido imediatamente."
        
    except Exception as e:
        return f"Erro ao cancelar execução: {str(e)}"

@mcp.tool()
def listar_execucoes() -> str:
    """
    Lista todas as execuções Tree of Thoughts (ativas e finalizadas).
    
    Retorna um resumo de todas as execuções armazenadas.
    """
    try:
        if not active_runs:
            return "Nenhuma execução encontrada."
        
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

@mcp.resource("config://defaults")
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
                "stop_conditions": {
                    "max_nodes": 50,
                    "max_time_seconds": 60
                },
                "evaluation_weights": {
                    "progress": 0.4,
                    "promise": 0.3,
                    "confidence": 0.3
                }
            }
            return json.dumps(default_config, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Erro ao obter configuração padrão: {str(e)}"

@mcp.resource("info://sobre")
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

if __name__ == "__main__":
    # Configurar variáveis de ambiente se necessário
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()
    
    # Executar o servidor MCP
    mcp.run()

