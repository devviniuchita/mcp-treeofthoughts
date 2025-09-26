import asyncio
import traceback
import uuid

from typing import Any
from typing import Dict
from typing import Optional

from fastapi import BackgroundTasks
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from src.graph import create_tot_graph
from src.models import GraphState
from src.models import RunConfig
from src.models import RunTask


app = FastAPI(title="MCP TreeOfThoughts API", version="0.1.0")

# In-memory storage for runs (for simplicity, replace with a database in production)
active_runs: Dict[str, Dict[str, Any]] = {}


class RunRequest(BaseModel):
    task: RunTask
    config: Optional[RunConfig] = None


@app.post("/run", response_model=Dict[str, str])
async def run_tot_process(req: RunRequest, background_tasks: BackgroundTasks):
    run_id = req.task.task_id if req.task.task_id else str(uuid.uuid4())
    config = req.config if req.config else RunConfig()

    if run_id in active_runs:
        raise HTTPException(
            status_code=409, detail=f"Run with ID {run_id} already exists."
        )

    # Initialize GraphState
    initial_state = GraphState(run_id=run_id, task=req.task, config=config)

    # Store initial state
    active_runs[run_id] = {
        "status": "running",
        "state": initial_state.model_dump(),
        "result": None,
    }

    # Create and compile the graph
    tot_graph = create_tot_graph()

    async def _run_in_background():
        try:
            # LangGraph run method returns the final state
            raw_final_state = await tot_graph.ainvoke(initial_state)
            # LangGraph might return a dict or a GraphState object
            if isinstance(raw_final_state, GraphState):
                final_state = raw_final_state
            else:
                # If it's a dict, try to parse it into GraphState for consistent access
                try:
                    final_state = GraphState(**raw_final_state)
                except Exception as e:
                    print(
                        f"[WARNING] Could not parse raw_final_state into GraphState: {e}. Raw state: {raw_final_state}"
                    )
                    # Fallback to a dict if parsing fails
                    final_state = raw_final_state

            active_runs[run_id]["status"] = "completed"
            # Ensure result is a dictionary for storage
            active_runs[run_id]["result"] = (
                final_state.model_dump()
                if isinstance(final_state, GraphState)
                else final_state
            )
            final_answer_text = (
                final_state.final_answer
                if isinstance(final_state, GraphState)
                else final_state.get("final_answer", "N/A")
            )
            print(f"Run {run_id} completed. Final Answer: {final_answer_text}")
        except Exception as e:
            active_runs[run_id]["status"] = "failed"
            active_runs[run_id]["error"] = str(e)
            import traceback

            error_traceback = traceback.format_exc()
            active_runs[run_id]["traceback"] = error_traceback
            print(f"Run {run_id} failed with error: {e}\nTraceback:\n{error_traceback}")

    background_tasks.add_task(_run_in_background)

    return {"run_id": run_id, "status": "started"}


@app.get("/status/{run_id}", response_model=Dict[str, Any])
async def get_run_status(run_id: str):
    run_data = active_runs.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found.")
    return {
        "run_id": run_id,
        "status": run_data["status"],
        "metrics": run_data["result"].get("metrics") if run_data["result"] else None,
    }


@app.get("/trace/{run_id}", response_model=Dict[str, Any])
async def get_run_trace(run_id: str):
    run_data = active_runs.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run_data["status"] == "running":
        return {
            "status": "running",
            "message": "Trace not available until run completes.",
            "current_state": run_data["state"],
        }
    return run_data["result"]


@app.post("/stop/{run_id}", response_model=Dict[str, str])
async def stop_run(run_id: str):
    # For LangGraph, stopping a run in progress is not straightforward without custom mechanisms.
    # This is a placeholder. In a real-world scenario, you'd need to implement a way to signal
    # the background task to stop, e.g., using an Event or a shared flag.
    if run_id not in active_runs:
        raise HTTPException(status_code=404, detail="Run not found.")
    if active_runs[run_id]["status"] == "running":
        active_runs[run_id][
            "status"
        ] = "cancelled"  # Mark as cancelled, but the background task might still run to completion
        return {
            "run_id": run_id,
            "status": "cancellation_requested",
            "message": "Cancellation mechanism not fully implemented for LangGraph background tasks. Task might complete.",
        }
    return {
        "run_id": run_id,
        "status": active_runs[run_id]["status"],
        "message": "Run is not active or already stopped.",
    }
