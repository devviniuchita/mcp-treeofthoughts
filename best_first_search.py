from typing import List, Dict, Any, Optional
from ..models import Node, GraphState
from .base import SearchStrategy

class BestFirstSearch(SearchStrategy):
    def __init__(self):
        pass # Best-first search typically doesn't need specific parameters like beam_width

    def select_nodes_for_expansion(self, state: GraphState) -> List[str]:
        """Seleciona o nó com a maior pontuação na fronteira para expansão."""
        if not state.frontier:
            return []
        # Best-first search expande apenas o melhor nó
        best_node_id = max(state.frontier, key=lambda node_id: state.nodes[node_id].score if state.nodes[node_id].score is not None else -1)
        return [best_node_id]

    def update_frontier(self, state: GraphState, new_nodes: List[Node]) -> GraphState:
        """Atualiza a fronteira com os novos nós gerados e mantém apenas os melhores."""
        # Remove o nó que foi expandido da fronteira (se ainda estiver lá)
        nodes_to_keep = [node_id for node_id in state.frontier if node_id not in [n.parent_id for n in new_nodes if n.parent_id is not None]]

        # Adiciona os novos nós à fronteira
        for node in new_nodes:
            if node.score is not None: # Apenas nós avaliados podem ser adicionados à fronteira
                nodes_to_keep.append(node.id)

        # Remove duplicatas e garante que a fronteira contém apenas IDs válidos
        state.frontier = list(set(nodes_to_keep))

        # Opcional: para manter a fronteira gerenciável, pode-se limitar o tamanho aqui
        # Por exemplo, manter apenas os top N nós por score
        # state.frontier.sort(key=lambda node_id: state.nodes[node_id].score if state.nodes[node_id].score is not None else -1, reverse=True)
        # state.frontier = state.frontier[:state.config.beam_width] # Reutilizando beam_width como um limite geral, ou adicionar um novo config

        return state

    def get_best_node(self, state: GraphState) -> Optional[Node]:
        """Retorna o melhor nó global encontrado até o momento, baseado na pontuação."""
        if not state.nodes:
            return None
        best_node_id = max(state.nodes.keys(), key=lambda node_id: state.nodes[node_id].score if state.nodes[node_id].score is not None else -1)
        return state.nodes[best_node_id]

