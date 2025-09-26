"""Helpers para enviar traces ao LangSmith."""

import os

from functools import wraps
from typing import Iterable

from langsmith import Client
from langsmith import run_helpers
from models import GraphState


def _read_bool_from_env(var_names: Iterable[str], default: bool = False) -> bool:
    for name in var_names:
        value = os.getenv(name)
        if value is not None:
            return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


class ToTTracer:
    """Facilita instrumentação de execuções com LangSmith."""

    def __init__(self) -> None:
        api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        api_url = os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT")
        project_name = (
            os.getenv("LANGSMITH_PROJECT")
            or os.getenv("LANGCHAIN_PROJECT")
            or "mcp-treeofthoughts"
        )

        client_kwargs = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if api_url:
            client_kwargs["api_url"] = api_url

        self.client = Client(**client_kwargs) if client_kwargs else Client()
        self.project_name = project_name
        self.tracing_enabled = _read_bool_from_env(
            ["LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"], default=True
        )

    def _should_trace(self) -> bool:
        return self.tracing_enabled

    def trace_tot_execution(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self._should_trace():
                return func(*args, **kwargs)

            run_id = kwargs.get("run_id", "unknown")
            with run_helpers.trace(
                f"tot_execution_{run_id}",
                run_type="chain",
                project_name=self.project_name,
                client=self.client,
                inputs={"args": args, "kwargs": kwargs},
            ) as run:
                try:
                    result = func(*args, **kwargs)
                    run.end(outputs={"status": "success", "result": result})
                    return result
                except Exception as err:
                    run.end(error=str(err))
                    raise

        return wrapper

    def trace_node_execution(self, node_name: str):
        def decorator(func):
            @wraps(func)
            def wrapper(state: GraphState, *args, **kwargs):
                if not self._should_trace():
                    return func(state, *args, **kwargs)

                with run_helpers.trace(
                    f"{node_name}_execution",
                    run_type="chain",
                    project_name=self.project_name,
                    client=self.client,
                    inputs={
                        "run_id": state.run_id,
                        "frontier_size": len(state.frontier),
                        "nodes_count": len(state.nodes),
                    },
                ) as run:
                    try:
                        result = func(state, *args, **kwargs)
                        run.end(
                            outputs={
                                "new_frontier_size": len(result.frontier),
                                "best_score": (
                                    result.nodes.get(result.best_node_id, {}).score
                                    if result.best_node_id
                                    else None
                                ),
                            }
                        )
                        return result
                    except Exception as err:
                        run.end(error=str(err))
                        raise

            return wrapper

        return decorator


# Instância global
tot_tracer = ToTTracer()
