"""Execution Management Service following enterprise patterns."""

import asyncio
import logging
import traceback

from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union
from uuid import uuid4

from .config.constants import DEFAULT_BEAM_WIDTH
from .config.constants import DEFAULT_BRANCHING_FACTOR
from .config.constants import DEFAULT_MAX_DEPTH
from .config.constants import DEFAULT_MAX_NODES
from .config.constants import DEFAULT_MAX_TIME_SECONDS
from .config.constants import ERROR_EXECUTION_NOT_FOUND
from .config.constants import ERROR_EXECUTION_NOT_RUNNING
from .exceptions import ExecutionNotFoundError
from .exceptions import ExecutionStateError
from .exceptions import GraphExecutionError
from .graph import create_tot_graph
from .models import GraphState
from .models import RunConfig
from .models import RunTask


logger = logging.getLogger(__name__)


class ExecutionManager:
    """Professional execution management following enterprise patterns."""

    def __init__(self) -> None:
        self.active_runs: Dict[str, Dict[str, Any]] = {}

    def create_execution(
        self,
        instruction: str,
        task_id: Optional[str] = None,
        constraints: Optional[str] = None,
        max_depth: int = DEFAULT_MAX_DEPTH,
        branching_factor: int = DEFAULT_BRANCHING_FACTOR,
        beam_width: int = DEFAULT_BEAM_WIDTH,
        max_nodes: int = DEFAULT_MAX_NODES,
        max_time_seconds: int = DEFAULT_MAX_TIME_SECONDS,
        strategy: str = "beam_search",
    ) -> str:
        """Create and start a new Tree of Thoughts execution."""
        run_id = task_id or str(uuid4())

        if run_id in self.active_runs:
            raise ExecutionStateError(f"Execução com ID {run_id} já existe.")

        try:
            # Create task and configuration
            task = RunTask(
                instruction=instruction, constraints=constraints, task_id=run_id
            )
            config = RunConfig(
                strategy=strategy,
                max_depth=max_depth,
                branching_factor=branching_factor,
                beam_width=beam_width,
                stop_conditions={
                    "max_nodes": max_nodes,
                    "max_time_seconds": max_time_seconds,
                },
            )

            # Initialize execution state
            self._initialize_execution_state(run_id, task, config)

            # Start background execution
            self._start_background_execution(run_id)

            logger.info(f"Execução {run_id} iniciada com estratégia {strategy}")
            return run_id

        except Exception as e:
            logger.error(f"Erro ao criar execução {run_id}: {e}")
            raise GraphExecutionError(
                f"Falha ao criar execução: {str(e)}", details={"run_id": run_id}
            ) from e

    def _initialize_execution_state(
        self, run_id: str, task: RunTask, config: RunConfig
    ) -> None:
        """Initialize execution state with proper tracking."""
        cancellation_event = asyncio.Event()
        initial_state = GraphState(run_id=run_id, task=task, config=config)
        initial_state.cancellation_event = cancellation_event

        self.active_runs[run_id] = {
            "status": "running",
            "state": initial_state.model_dump(),
            "result": None,
            "start_time": datetime.now().isoformat(),
            "cancellation_event": cancellation_event,
            "task": None,
        }

    def _start_background_execution(self, run_id: str) -> None:
        """Start Tree of Thoughts execution in background."""
        initial_state_data = self.active_runs[run_id]["state"]
        initial_state = GraphState(**initial_state_data)
        initial_state.cancellation_event = self.active_runs[run_id][
            "cancellation_event"
        ]

        async def execute_graph():
            """Execute the Tree of Thoughts graph with proper error handling."""
            try:
                tot_graph = create_tot_graph()
                raw_final_state = await tot_graph.ainvoke(initial_state)

                # Check if cancelled during execution
                if initial_state.cancellation_event.is_set():
                    self._mark_execution_cancelled(run_id)
                    return

                # Process final state
                final_state = self._process_final_state(raw_final_state)
                self._mark_execution_completed(run_id, final_state)

            except asyncio.CancelledError:
                self._mark_execution_cancelled(run_id)
                raise
            except Exception as e:
                self._mark_execution_failed(run_id, e)
                logger.error(f"Execução {run_id} falhou: {e}")

        # Schedule execution in background
        task_ref = self._schedule_background_task(execute_graph())
        self.active_runs[run_id]["task"] = task_ref

    def _process_final_state(self, raw_final_state: Any) -> Dict[str, Any]:
        """Process and convert final state to serializable format."""
        try:
            if isinstance(raw_final_state, GraphState):
                return raw_final_state.model_dump()
            else:
                return GraphState(**raw_final_state).model_dump()
        except Exception as e:
            logger.warning(f"Não foi possível converter final_state: {e}")
            return raw_final_state if isinstance(raw_final_state, dict) else {}

    def _mark_execution_completed(
        self, run_id: str, final_state: Dict[str, Any]
    ) -> None:
        """Mark execution as completed with results."""
        self.active_runs[run_id].update(
            {
                "status": "completed",
                "result": final_state,
                "end_time": datetime.now().isoformat(),
            }
        )

        final_answer = final_state.get("final_answer", "N/A")
        logger.info(f"Execução {run_id} concluída. Resposta: {final_answer}")

    def _mark_execution_cancelled(self, run_id: str) -> None:
        """Mark execution as cancelled."""
        self.active_runs[run_id].update(
            {
                "status": "cancelled",
                "end_time": datetime.now().isoformat(),
            }
        )
        logger.info(f"Execução {run_id} foi cancelada")

    def _mark_execution_failed(self, run_id: str, error: Exception) -> None:
        """Mark execution as failed with error details."""
        self.active_runs[run_id].update(
            {
                "status": "failed",
                "error": str(error),
                "traceback": traceback.format_exc(),
                "end_time": datetime.now().isoformat(),
            }
        )

    def _schedule_background_task(self, coro) -> Union[asyncio.Task, asyncio.Future]:
        """Schedule coroutine in appropriate event loop."""
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(coro)
        except RuntimeError:
            # Handle case where no event loop is running
            from .utils.event_loop import get_or_create_event_loop

            loop = get_or_create_event_loop()
            return asyncio.run_coroutine_threadsafe(coro, loop)

    def get_execution_status(self, run_id: str) -> Dict[str, Any]:
        """Get detailed status of execution."""
        if run_id not in self.active_runs:
            raise ExecutionNotFoundError(
                ERROR_EXECUTION_NOT_FOUND.format(run_id=run_id)
            )

        run_data = self.active_runs[run_id]
        status_info = {
            "run_id": run_id,
            "status": run_data["status"],
            "start_time": run_data.get("start_time"),
            "end_time": run_data.get("end_time"),
        }

        if run_data.get("result") and run_data["result"].get("metrics"):
            status_info["metrics"] = run_data["result"]["metrics"]

        if run_data.get("error"):
            status_info["error"] = run_data["error"]

        return status_info

    def get_execution_result(self, run_id: str) -> Dict[str, Any]:
        """Get complete execution result."""
        if run_id not in self.active_runs:
            raise ExecutionNotFoundError(
                ERROR_EXECUTION_NOT_FOUND.format(run_id=run_id)
            )

        run_data = self.active_runs[run_id]
        status = run_data["status"]

        result_info = {
            "run_id": run_id,
            "status": status,
        }

        if status == "completed":
            result = run_data.get("result", {})
            result_info.update(
                {
                    "final_answer": result.get("final_answer", "N/A"),
                    "metrics": result.get("metrics", {}),
                }
            )
        elif status == "failed":
            result_info["error"] = run_data.get("error", "Erro desconhecido")

        return result_info

    def cancel_execution(self, run_id: str) -> None:
        """Cancel running execution immediately."""
        if run_id not in self.active_runs:
            raise ExecutionNotFoundError(
                ERROR_EXECUTION_NOT_FOUND.format(run_id=run_id)
            )

        run_data = self.active_runs[run_id]
        if run_data["status"] != "running":
            raise ExecutionStateError(
                ERROR_EXECUTION_NOT_RUNNING.format(
                    run_id=run_id, status=run_data["status"]
                )
            )

        # Signal cancellation
        cancellation_event = run_data.get("cancellation_event")
        if cancellation_event:
            cancellation_event.set()

        # Cancel asyncio task
        task_ref = run_data.get("task")
        if task_ref and not task_ref.done():
            task_ref.cancel()

        # Update status immediately
        self._mark_execution_cancelled(run_id)
        logger.info(f"Execução {run_id} cancelada com sucesso")

    def list_executions(self) -> Dict[str, Any]:
        """List all executions with summary information."""
        if not self.active_runs:
            return {"executions": [], "total": 0}

        executions = []
        for run_id, run_data in self.active_runs.items():
            execution_info = {
                "run_id": run_id,
                "status": run_data["status"],
                "start_time": run_data.get("start_time"),
                "end_time": run_data.get("end_time"),
            }

            # Add preview of result if available
            if run_data.get("result") and run_data["result"].get("final_answer"):
                answer = run_data["result"]["final_answer"]
                preview = answer[:100] + "..." if len(answer) > 100 else answer
                execution_info["answer_preview"] = preview

            executions.append(execution_info)

        return {"executions": executions, "total": len(executions)}
