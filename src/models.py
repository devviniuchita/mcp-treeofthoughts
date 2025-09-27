from __future__ import annotations

import asyncio
import threading
import time
import uuid

from contextlib import contextmanager
from enum import Enum
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import PrivateAttr
from pydantic import ValidationInfo
from pydantic import field_validator


if TYPE_CHECKING:
    from src.semantic_cache import SemanticCache as SemanticCacheType
else:  # pragma: no cover - fallback para execução sem cache
    SemanticCacheType = Any  # type: ignore[misc, assignment]


class ValidationLevel(Enum):
    """Níveis de validação disponíveis"""

    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"


class CacheRequiredError(Exception):
    """Exceção levantada quando semantic cache é necessário mas não inicializado"""


class RunConfig(BaseModel):
    strategy: str = 'beam_search'  # Corrigido: removido campo duplicado
    branching_factor: int = 3
    max_depth: int = 2
    beam_width: int = 5
    propose_temp: float = 0.7
    value_temp: float = 0.2
    use_value_model: bool = False
    parallelism: int = 4
    per_node_token_estimate: int = 150
    stop_conditions: Dict[str, Any] = Field(
        default_factory=lambda: {"max_nodes": 200, "max_time_seconds": 30}
    )
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 3072  # Default for gemini-embedding-001
    evaluation_weights: Dict[str, float] = Field(
        default_factory=lambda: {"progress": 0.4, "promise": 0.3, "confidence": 0.3}
    )
    use_reranker: bool = False
    reranker_model: str = "BAAI/bge-reranker-base"
    reranker_top_n: int = 3


class RunTask(BaseModel):
    task_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str
    constraints: Optional[str] = ''
    history: List[str] = Field(default_factory=list)


class Candidate(BaseModel):
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class ValueScore(BaseModel):
    progress: float = Field(..., ge=0, le=10)
    promise: float = Field(..., ge=0, le=10)
    confidence: float = Field(..., ge=0, le=10)
    justification: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class Node(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    parent_id: Optional[str] = None
    depth: int = 0
    score: Optional[float] = None
    raw_scores: Optional[ValueScore] = None
    children_ids: List[str] = Field(default_factory=list)
    is_solution: bool = False
    reranker_score: Optional[float] = None

    def path_texts(self, all_nodes: Dict[str, 'Node']) -> List[str]:
        parts = []
        node = self
        while node:
            parts.append(node.text)
            if node.parent_id:
                node = all_nodes.get(node.parent_id)
            else:
                node = None
        return list(reversed(parts))

    def path_string(self, all_nodes: Dict[str, 'Node']) -> str:
        return '\n'.join(self.path_texts(all_nodes))


class GraphState(BaseModel):
    run_id: str
    task: RunTask
    config: RunConfig
    nodes: Dict[str, Node] = Field(default_factory=dict)
    frontier: List[str] = Field(default_factory=list)  # List of node IDs
    root_id: Optional[str] = None
    best_node_id: Optional[str] = None
    nodes_expanded: int = 0
    start_time: float = Field(default_factory=time.time)
    final_answer: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    stop_reason: Optional[str] = None

    # Campos privados não serializáveis
    _semantic_cache: Optional[SemanticCacheType] = PrivateAttr(default=None)
    _cancellation_event: Optional[asyncio.Event] = PrivateAttr(default=None)
    _thread_lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)
    _validation_level: ValidationLevel = PrivateAttr(default=ValidationLevel.BASIC)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    def __init__(self, **data):
        """Inicialização com configuração automática do estado de runtime"""
        super().__init__(**data)
        self.initialize_runtime_state()
        # Validação inicial automática
        if not self.validate_state(level=ValidationLevel.BASIC):
            raise ValueError("Estado inicial inconsistente")

    @property
    def semantic_cache(self) -> Optional[SemanticCacheType]:
        """Acesso ao cache semântico (não serializado)"""
        return self._semantic_cache

    @semantic_cache.setter
    def semantic_cache(self, value: Optional[SemanticCacheType]) -> None:
        """Define o cache semântico com thread safety"""
        with self._thread_lock:
            self._semantic_cache = value

    def get_semantic_cache_required(self) -> SemanticCacheType:
        """Obtém o cache semântico, levantando exceção se não inicializado"""
        if self._semantic_cache is None:
            raise CacheRequiredError(
                "Semantic cache não foi inicializado. "
                "Defina semantic_cache antes de usar operações que requerem cache."
            )
        return self._semantic_cache

    @property
    def cancellation_event(self) -> Optional[asyncio.Event]:
        """Acesso ao evento de cancelamento (não serializado)"""
        return self._cancellation_event

    @cancellation_event.setter
    def cancellation_event(self, value: Optional[asyncio.Event]) -> None:
        """Define o evento de cancelamento com thread safety"""
        with self._thread_lock:
            self._cancellation_event = value

    @property
    def validation_level(self) -> ValidationLevel:
        """Nível atual de validação"""
        return self._validation_level

    @validation_level.setter
    def validation_level(self, level: ValidationLevel) -> None:
        """Define o nível de validação"""
        self._validation_level = level

    @classmethod
    def create(
        cls,
        run_id: str,
        task: RunTask,
        config: RunConfig,
        validation_level: ValidationLevel = ValidationLevel.BASIC,
    ) -> 'GraphState':
        """Factory method para criação com inicialização adequada"""
        state = cls(run_id=run_id, task=task, config=config)
        state.validation_level = validation_level
        return state  # __init__ já chama initialize_runtime_state()

    def initialize_runtime_state(self) -> None:
        """Inicializa o estado não serializável para runtime (thread-safe)"""
        with self._thread_lock:
            if self._cancellation_event is None:
                self._cancellation_event = asyncio.Event()

    def model_copy(self, *args, **kwargs):  # type: ignore[override]
        """Garante que cópias recebem locks e eventos próprios."""

        copied = super().model_copy(*args, **kwargs)
        if isinstance(copied, GraphState):
            copied._thread_lock = threading.RLock()
            copied._cancellation_event = asyncio.Event()
            copied._semantic_cache = None
            copied._validation_level = self._validation_level
        return copied

    def __deepcopy__(self, memo: Optional[Dict[int, Any]] = None) -> 'GraphState':
        """Suporte explícito a copy.deepcopy sem copiar locks nativos."""

        if memo is None:
            memo = {}

        if id(self) in memo:
            return memo[id(self)]

        copied = self.model_copy(deep=True)
        memo[id(self)] = copied
        return copied

    def validate_state(self, level: Optional[ValidationLevel] = None) -> bool:
        """
        Valida se o estado está consistente

        Args:
            level: Nível de validação (usa self._validation_level se None)
        """
        validation_level = level or self._validation_level

        if validation_level == ValidationLevel.NONE:
            return True

        # Validação básica
        if validation_level in [ValidationLevel.BASIC, ValidationLevel.STRICT]:
            if self.root_id and self.root_id not in self.nodes:
                return False
            if self.best_node_id and self.best_node_id not in self.nodes:
                return False
            if not all(node_id in self.nodes for node_id in self.frontier):
                return False

        # Validação estrita adicional
        if validation_level == ValidationLevel.STRICT:
            # Verifica se todos os parent_ids são válidos
            for node in self.nodes.values():
                if node.parent_id and node.parent_id not in self.nodes:
                    return False

            # Verifica se todas as children_ids são válidas
            for node in self.nodes.values():
                if not all(child_id in self.nodes for child_id in node.children_ids):
                    return False

            # Verifica consistência parent-child
            for node in self.nodes.values():
                if node.parent_id:
                    parent = self.nodes[node.parent_id]
                    if node.id not in parent.children_ids:
                        return False

        return True

    def ensure_valid_state(self, level: Optional[ValidationLevel] = None) -> None:
        """Garante que o estado é válido, levantando exceção se não for"""
        if not self.validate_state(level):
            raise ValueError(
                "Estado inconsistente detectado "
                f"(level: {level or self._validation_level})"
            )

    @field_validator("root_id", "best_node_id")
    @classmethod
    def validate_node_references(
        cls, value: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        """Validador Pydantic para referências de nós."""

        if value is None:
            return value

        nodes = info.data.get("nodes") if info.data is not None else None
        if isinstance(nodes, dict) and value not in nodes:
            raise ValueError(f"Node ID {value} não existe em nodes")

        return value

    def is_cancelled(self) -> bool:
        """Verifica se a execução foi cancelada (thread-safe)"""
        with self._thread_lock:
            return (
                self._cancellation_event is not None
                and self._cancellation_event.is_set()
            )

    def cancel(self) -> None:
        """Cancela a execução atual (thread-safe)"""
        with self._thread_lock:
            if self._cancellation_event is not None:
                self._cancellation_event.set()

    def reset_cancellation(self) -> None:
        """Reseta o estado de cancelamento (thread-safe)"""
        with self._thread_lock:
            if self._cancellation_event is not None:
                self._cancellation_event.clear()

    async def check_cancellation(self) -> None:
        """Verifica cancelamento e levanta exceção se cancelado"""
        if self.is_cancelled():
            raise asyncio.CancelledError("Operation cancelled")

    @contextmanager
    def cancellation_context(self):
        """Context manager para operações com suporte a cancelamento"""
        if self.is_cancelled():
            raise asyncio.CancelledError("Operation cancelled")
        try:
            yield self
        except asyncio.CancelledError:
            self.cancel()
            raise

    @contextmanager
    def thread_safe_operation(self):
        """Context manager para operações thread-safe"""
        with self._thread_lock:
            yield self

    def add_node_safe(self, node: Node) -> None:
        """Adiciona um nó de forma thread-safe com validação"""
        with self._thread_lock:
            self.nodes[node.id] = node
            # Validação automática se configurada
            if self._validation_level != ValidationLevel.NONE:
                if not self.validate_state():
                    # Rollback em caso de estado inválido
                    del self.nodes[node.id]
                    raise ValueError(
                        f"Adicionar nó {node.id} resultaria em estado inválido"
                    )

    def update_frontier_safe(self, frontier: List[str]) -> None:
        """Atualiza frontier de forma thread-safe com validação"""
        with self._thread_lock:
            old_frontier = self.frontier.copy()
            self.frontier = frontier
            # Validação automática se configurada
            if self._validation_level != ValidationLevel.NONE:
                if not self.validate_state():
                    # Rollback em caso de estado inválido
                    self.frontier = old_frontier
                    raise ValueError("Atualizar frontier resultaria em estado inválido")

    def dict_with_validation(self, **kwargs) -> Dict[str, Any]:
        """Serializa com validação prévia"""
        self.ensure_valid_state()
        return self.dict(**kwargs)

    def json_with_validation(self, **kwargs) -> str:
        """Serializa para JSON com validação prévia"""
        self.ensure_valid_state()
        return self.json(**kwargs)
