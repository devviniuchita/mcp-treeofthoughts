from typing import List, Dict, Any, Optional
from ..models import Node, GraphState
from .base import SearchStrategy

class BeamSearch(SearchStrategy):
    def __init__(self, beam_width: int):
        self.beam_width = beam_width

    def select_nodes_for_expansion(self, state: GraphState) -> List[str]:
        # Beam search typically expands the best nodes in the frontier.
        # The frontier should already be sorted by score (handled in update_frontier).
        # We select all nodes in the current frontier for expansion in a given step.
        # The pruning happens when updating the frontier.
        return state.frontier

    def update_frontier(self, state: GraphState, new_nodes: List[Node]) -> GraphState:
        # Add new nodes to the existing frontier (temporarily using their IDs)
        current_frontier_nodes = [state.nodes[node_id] for node_id in state.frontier]
        all_nodes_for_consideration = current_frontier_nodes + new_nodes

        # Filter out nodes that exceed max_depth
        valid_nodes = [node for node in all_nodes_for_consideration if node.depth < state.config.max_depth]

        # Sort all valid nodes by score in descending order
        # Nodes without a score (e.g., root before evaluation) should be handled gracefully, perhaps at the end.
        valid_nodes.sort(key=lambda node: node.score if node.score is not None else -1, reverse=True)

        # Select the top 'beam_width' nodes for the new frontier
        state.frontier = [node.id for node in valid_nodes[:self.beam_width]]

        # Update best_node_id if a better node is found
        if state.frontier:
            current_best_node = state.nodes.get(state.best_node_id)
            new_best_candidate = state.nodes[state.frontier[0]]
            if current_best_node is None or (new_best_candidate.score is not None and new_best_candidate.score > (current_best_node.score if current_best_node.score is not None else -1)):
                state.best_node_id = new_best_candidate.id

        return state

    def get_best_node(self, state: GraphState) -> Optional[Node]:
        if state.best_node_id:
            return state.nodes.get(state.best_node_id)
        return None
