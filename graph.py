from typing import Any
from typing import List
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import StateGraph
from models import GraphState
from models import Node
from models import RunConfig
from models import RunTask
from nodes import check_stop_condition
from nodes import evaluate_thoughts
from nodes import finalize_solution
from nodes import initialize_graph
from nodes import propose_thoughts
from nodes import rerank_thoughts
from nodes import select_and_prune


def create_tot_graph():
    workflow = StateGraph(GraphState)

    # Add nodes to the graph
    workflow.add_node("initialize", initialize_graph)
    workflow.add_node("propose", propose_thoughts)
    workflow.add_node("rerank", rerank_thoughts)
    workflow.add_node("evaluate", evaluate_thoughts)

    workflow.add_node("select", select_and_prune)
    workflow.add_node("finalize", finalize_solution)

    # Set the entry point
    workflow.set_entry_point("initialize")

    # Define the edges
    workflow.add_edge("initialize", "propose")
    workflow.add_edge("propose", "rerank")
    workflow.add_edge("rerank", "evaluate")
    workflow.add_edge("evaluate", "select")

    # Conditional edge from select based on stop condition
    workflow.add_conditional_edges(
        "select",
        check_stop_condition,
        {
            "continue": "propose",  # Loop back to propose if not stopped
            "finalize": "finalize",  # Go to finalize if stop condition met
        },
    )
    workflow.add_edge("finalize", END)

    return workflow.compile()
