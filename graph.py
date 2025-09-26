from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from .models import GraphState, Node, RunConfig, RunTask
from .nodes import initialize_graph, propose_thoughts, evaluate_thoughts, select_and_prune, check_stop_condition, finalize_solution, rerank_thoughts


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
            "continue": "propose", # Loop back to propose if not stopped
            "finalize": "finalize" # Go to finalize if stop condition met
        }
    )
    workflow.add_edge("finalize", END)

    return workflow.compile()

