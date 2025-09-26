from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import List
from typing import Optional

from models import GraphState
from models import Node


class SearchStrategy(ABC):
    @abstractmethod
    def select_nodes_for_expansion(self, state: GraphState) -> List[str]:
        """Seleciona os IDs dos nós da fronteira para expansão."""
        pass

    @abstractmethod
    def update_frontier(self, state: GraphState, new_nodes: List[Node]) -> GraphState:
        """Atualiza a fronteira com novos nós, aplicando poda se necessário."""
        pass

    @abstractmethod
    def get_best_node(self, state: GraphState) -> Optional[Node]:
        """Retorna o melhor nó encontrado até o momento."""
        pass
