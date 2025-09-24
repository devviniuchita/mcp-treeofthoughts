from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
import uuid

class RunConfig(BaseModel):
    strategy: str = 'balanced'
    branching_factor: int = 3
    max_depth: int = 2
    beam_width: int = 5
    propose_temp: float = 0.7
    value_temp: float = 0.2
    use_value_model: bool = False
    parallelism: int = 4
    per_node_token_estimate: int = 150
    stop_conditions: Dict[str, Any] = Field(default_factory=lambda: {"max_nodes":200, "max_time_seconds":30})
    strategy: str = "beam_search" # Default strategy
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 3072 # Default for gemini-embedding-001
    evaluation_weights: Dict[str, float] = Field(default_factory=lambda: {"progress": 0.4, "promise": 0.3, "confidence": 0.3})

class RunTask(BaseModel):
    task_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str
    constraints: Optional[str] = ''
    history: Optional[List[str]] = []

class Candidate(BaseModel):
    text: str
    meta: Optional[Dict[str, Any]] = {}

class ValueScore(BaseModel):
    progress: float = Field(..., ge=0, le=10)
    promise: float = Field(..., ge=0, le=10)
    confidence: float = Field(..., ge=0, le=10)
    justification: str
    meta: Optional[Dict[str, Any]] = {}

class Node(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    parent_id: Optional[str] = None
    depth: int = 0
    score: Optional[float] = None
    raw_scores: Optional[ValueScore] = None
    children_ids: List[str] = []
    is_solution: bool = False

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
    frontier: List[str] = Field(default_factory=list) # List of node IDs
    root_id: Optional[str] = None
    best_node_id: Optional[str] = None
    nodes_expanded: int = 0
    start_time: float = Field(default_factory=lambda: time.time())
    final_answer: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    stop_reason: Optional[str] = None
    semantic_cache: Any = Field(default=None, exclude=True) # Exclude from serialization

    class Config:
        arbitrary_types_allowed = True

import time

