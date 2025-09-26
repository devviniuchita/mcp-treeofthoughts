from typing import Any
from typing import Dict
from typing import Optional

from langchain_core.output_parsers import JsonOutputParser
from llm_client import get_chat_llm
from models import Node
from models import RunConfig
from models import ValueScore
from prompts import VALUE_PROMPT
from pydantic import BaseModel
from pydantic import Field


class LLMValueScore(BaseModel):
    progress: float = Field(..., ge=0, le=10)
    promise: float = Field(..., ge=0, le=10)
    confidence: float = Field(..., ge=0, le=10)
    justification: str


class HybridEvaluator:
    def __init__(self, config: RunConfig):
        self.config = config
        self.llm = get_chat_llm(
            model="gemini-2.5-flash", temperature=self.config.value_temp
        )
        self.structured_llm = self.llm.with_structured_output(LLMValueScore)

    def _llm_evaluate(
        self, task_instruction: str, candidate_text: str, history_text: str
    ) -> ValueScore:
        prompt = VALUE_PROMPT.format(
            task=task_instruction, candidate=candidate_text, history=history_text
        )
        try:
            llm_output: LLMValueScore = self.structured_llm.invoke(prompt)
            return ValueScore(
                progress=llm_output.progress,
                promise=llm_output.promise,
                confidence=llm_output.confidence,
                justification=llm_output.justification,
            )
        except Exception as e:
            print(f"Error parsing LLM evaluation: {e}. Raw output might be: {e.args}")
            # Fallback to a default low score if parsing fails
            return ValueScore(
                progress=0.0,
                promise=0.0,
                confidence=0.0,
                justification=f"Parsing error: {e}",
            )

    def _apply_heuristics(self, node: Node, task_instruction: str) -> Optional[float]:
        # Example heuristic: penalize thoughts that are too short or too long
        if len(node.text) < 10 or len(node.text) > 500:  # Arbitrary limits
            return 0.1  # Very low score
        # Add more heuristics here based on task type or common pitfalls
        return None  # No heuristic applied, proceed with LLM evaluation

    def evaluate(
        self, node: Node, task_instruction: str, all_nodes: Dict[str, Node]
    ) -> Node:
        # 1. Apply Heuristics first (cheap check)
        heuristic_score = self._apply_heuristics(node, task_instruction)
        if heuristic_score is not None:
            node.score = heuristic_score
            node.raw_scores = ValueScore(
                progress=heuristic_score,
                promise=heuristic_score,
                confidence=heuristic_score,
                justification="Heuristic low score",
            )
            return node

        # 2. If no strong heuristic, use LLM evaluation
        history_text = node.path_string(all_nodes)
        llm_raw_scores = self._llm_evaluate(task_instruction, node.text, history_text)
        node.raw_scores = llm_raw_scores

        # 3. Calculate final weighted score
        weights = self.config.evaluation_weights
        final_score = (
            llm_raw_scores.progress * weights.get("progress", 0.4)
            + llm_raw_scores.promise * weights.get("promise", 0.3)
            + llm_raw_scores.confidence * weights.get("confidence", 0.3)
        )
        # Normalize to 0-10 scale if weights sum to 1
        node.score = final_score
        return node
