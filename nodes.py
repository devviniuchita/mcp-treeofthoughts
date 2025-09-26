import time
import json
import os
from typing import List, Dict, Any, Tuple
from src.llm_client import get_chat_llm
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from .models import GraphState, Node, Candidate, ValueScore, RunConfig, RunTask
from .prompts import PROPOSE_PROMPT, FINALIZE_PROMPT
from .evaluation.hybrid_evaluator import HybridEvaluator, LLMValueScore
from .cache.semantic_cache import SemanticCache
from .strategies.beam_search import BeamSearch # Assuming BeamSearch as default
from src.reranker.bge_reranker import BGEReranker

# Initialize LLM for proposing thoughts
propose_llm = get_chat_llm(model="gemini-2.5-flash", temperature=0.7) # Will be updated to use state.config.propose_temp later

# Initialize Semantic Cache (global or passed via state)
# semantic_cache will be initialized in initialize_graph

def initialize_graph(state: GraphState) -> GraphState:
    """Inicializa o estado do grafo com o nó raiz."""
    root_node = Node(text=state.task.instruction, parent_id=None, depth=0)
    state.nodes[root_node.id] = root_node
    state.root_id = root_node.id
    state.frontier = [root_node.id]
    state.best_node_id = root_node.id # Initialize best node as root
    state.start_time = time.time()
    # Initialize Semantic Cache here to access state.config
    state.semantic_cache = SemanticCache(
        embedding_model_name=state.config.embedding_model,
        dimension=state.config.embedding_dim, # Use the dimension from RunConfig
        google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )




    print(f"[INIT] Initialized graph for task: {state.task.instruction}")
    return state

def propose_thoughts(state: GraphState) -> GraphState:
    """Gera novos pensamentos (candidatos) para os nós na fronteira."""
    if not state.frontier:
        print("[PROPOSE] Frontier is empty, cannot propose.")
        return state

    nodes_to_expand_ids = state.frontier # For beam search, we expand all in frontier
    new_nodes_generated = []

    for node_id in nodes_to_expand_ids:
        node = state.nodes[node_id]
        if node.depth >= state.config.max_depth:
            continue # Skip if max depth reached

        # Check semantic cache before proposing
        cache_key = f"propose:{node.path_string(state.nodes)}:{state.task.constraints}"
        cached_results = state.semantic_cache.search(cache_key, k=1, min_score=0.75) # Using min_score for cosine similarity

        candidates_text = []
        if cached_results:
            print(f"[CACHE HIT] Propose for node {node.id} from cache.")
            if "candidates" in cached_results[0]["metadata"]:
                candidates_text = json.loads(cached_results[0]["metadata"]["candidates"])
            else:
                print(f"[CACHE MISS] \'candidates\' key not found in cache metadata for node {node.id}. Proceeding with LLM call.")

        if not candidates_text: # If no candidates from cache, or cache miss, call LLM
            print(f"[PROPOSE] Proposing for node: {node.id} (depth {node.depth})")
            prompt = PROPOSE_PROMPT.format(
                k=state.config.branching_factor,
                task=state.task.instruction,
                history=node.path_string(state.nodes),
                constraints=state.task.constraints
            )
            try:
                raw_output = propose_llm.invoke(prompt).content
                # Extract JSON from markdown code block if present
                if raw_output.strip().startswith("```json") and raw_output.strip().endswith("```"):
                    raw_output = raw_output.strip()[len("```json"):-len("```")].strip()
                # Attempt to parse JSON array
                candidates_text = json.loads(raw_output)
                if not isinstance(candidates_text, list):
                    raise ValueError("LLM did not return a JSON array.")
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON decode error in propose_thoughts: {e}. Raw output: {raw_output}")
                # Fallback: split by lines if JSON parsing fails
                candidates_text = [t.strip() for t in raw_output.split('\n') if t.strip()][:state.config.branching_factor]
            except Exception as e:
                print(f"[ERROR] Unexpected error in propose_thoughts: {e}. Raw output: {raw_output}")
                candidates_text = []

            # Add to semantic cache
            state.semantic_cache.add(cache_key, metadata={"candidates": json.dumps(candidates_text)})

        for candidate_text in candidates_text[:state.config.branching_factor]:
            child_node = Node(text=candidate_text, parent_id=node.id, depth=node.depth + 1)
            state.nodes[child_node.id] = child_node
            node.children_ids.append(child_node.id)
            new_nodes_generated.append(child_node)

    state.nodes_expanded += len(nodes_to_expand_ids)
    state.frontier = [n.id for n in new_nodes_generated] # Frontier now contains newly generated nodes to be evaluated
    return state

def evaluate_thoughts(state: GraphState) -> GraphState:
    """Avalia os pensamentos recém-gerados na fronteira."""
    if not state.frontier:
        print("[EVALUATE] Frontier is empty, nothing to evaluate.")
        return state

    evaluator = HybridEvaluator(state.config)
    evaluated_nodes = []

    for node_id in state.frontier:
        node = state.nodes[node_id]
        print(f"[EVALUATE] Evaluating node: {node.id} (depth {node.depth})")

        # Check semantic cache for evaluation
        cache_key = f"evaluate:{node.path_string(state.nodes)}:{state.task.instruction}"
        cached_results = state.semantic_cache.search(cache_key, k=1, min_score=0.75) # Using min_score for cosine similarity

        evaluated_node = None
        if cached_results:
            metadata = cached_results[0]["metadata"]
            if "score" in metadata and "raw_scores" in metadata:
                try:
                    node.score = metadata["score"]
                    raw_scores_dict = json.loads(metadata["raw_scores"])
                    node.raw_scores = ValueScore(**raw_scores_dict)
                    evaluated_node = node # Use the node updated from cache
                    print(f"[CACHE HIT] Evaluation for node {node.id} from cache.")
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[CACHE MISS] Error parsing cached evaluation for node {node.id}: {e}. Proceeding with LLM call.")
            else:
                print(f"[CACHE MISS] Missing 'score' or 'raw_scores' in cached metadata for node {node.id}. Proceeding with LLM call.")

        if evaluated_node is None: # If not from cache (or cache was invalid), call LLM
            evaluated_node = evaluator.evaluate(node, state.task.instruction, state.nodes)
            state.nodes[node_id] = evaluated_node # Update the node in the state
            # Add to semantic cache
            state.semantic_cache.add(cache_key, metadata={
                "score": evaluated_node.score,
                "raw_scores": evaluated_node.raw_scores.model_dump_json() if isinstance(evaluated_node.raw_scores, BaseModel) else json.dumps(evaluated_node.raw_scores)
            })
        evaluated_nodes.append(evaluated_node) # Append the (potentially updated) evaluated_node

    # Update frontier to contain the IDs of the evaluated nodes, sorted by score
    evaluated_nodes.sort(key=lambda n: n.score if n.score is not None else -1, reverse=True)
    state.frontier = [n.id for n in evaluated_nodes]

    return state

def select_and_prune(state: GraphState) -> GraphState:
    """Aplica a estratégia de busca para selecionar e podar nós."""
    if not state.frontier:
        print("[SELECT] Frontier is empty, nothing to select/prune.")
        return state

    # Instantiate the selected strategy (e.g., BeamSearch)
    # This could be dynamic based on state.config.strategy
    strategy = BeamSearch(beam_width=state.config.beam_width)

    # The BeamSearch strategy\'s update_frontier method handles selection and pruning
    state = strategy.update_frontier(state, [state.nodes[node_id] for node_id in state.frontier])

    # Update best_node_id based on the strategy\'s current best
    best_node_from_strategy = strategy.get_best_node(state)
    if best_node_from_strategy:
        current_best_overall = state.nodes.get(state.best_node_id)
        if current_best_overall is None or (best_node_from_strategy.score is not None and best_node_from_strategy.score > (current_best_overall.score if current_best_overall.score is not None else -1)):
            state.best_node_id = best_node_from_strategy.id

    print(f"[SELECT] Frontier after selection/pruning: {len(state.frontier)} nodes. Best node score: {state.nodes[state.best_node_id].score if state.best_node_id else 'N/A'}")
    return state

def check_stop_condition(state: GraphState) -> str:
    """Verifica as condições de parada do algoritmo ToT."""
    current_best_node = state.nodes.get(state.best_node_id)

    # Condition 1: Max nodes expanded
    if state.nodes_expanded >= state.config.stop_conditions.get("max_nodes", 200):
        state.stop_reason = "Max nodes expanded"
        print(f"[STOP] Max nodes expanded: {state.nodes_expanded}")
        return "finalize"

    # Condition 2: Max time elapsed
    if (time.time() - state.start_time) >= state.config.stop_conditions.get("max_time_seconds", 30):
        state.stop_reason = "Max time elapsed"
        print(f"[STOP] Max time elapsed: {time.time() - state.start_time:.2f}s")
        return "finalize"

    # Condition 3: Solution found (high score)
    if current_best_node and current_best_node.score is not None and current_best_node.score >= 9.5:
        state.stop_reason = "High score achieved"
        print(f"[STOP] High score achieved: {current_best_node.score}")
        return "finalize"

    # Condition 4: Frontier is empty (no more paths to explore)
    if not state.frontier:
        state.stop_reason = "Frontier empty"
        print("[STOP] Frontier is empty.")
        return "finalize"

    # Condition 5: Max depth reached for all nodes in frontier (handled by strategy.update_frontier, but good to have a final check)
    # If all nodes in frontier are at max_depth, and no solution found, then finalize.
    if all(state.nodes[node_id].depth >= state.config.max_depth for node_id in state.frontier):
        state.stop_reason = "All nodes reached max depth"
        print("[STOP] All nodes in frontier reached max depth.")
        return "finalize"

    print(f"[CONTINUE] Current best score: {current_best_node.score if current_best_node else 'N/A'}. Nodes expanded: {state.nodes_expanded}. Frontier size: {len(state.frontier)}")
    return "continue"

def finalize_solution(state: GraphState) -> GraphState:
    """Gera a resposta final a partir do melhor caminho encontrado."""
    best_node = state.nodes.get(state.best_node_id)
    if not best_node:
        state.final_answer = "No solution found." # Fallback if no best node is identified
        print("[FINALIZE] No best node found.")
        return state

    print(f"[FINALIZE] Finalizing solution from best node: {best_node.id} with score {best_node.score}")
    chain_text = best_node.path_string(state.nodes)
    prompt = FINALIZE_PROMPT.format(chain=chain_text)

    # Use a lower temperature for final answer generation for determinism
    final_llm = get_chat_llm(model="gemini-2.5-flash", temperature=0.0) # Use a lower temperature for final answer generation for determinism
    final_answer = final_llm.invoke(prompt).content
    state.final_answer = final_answer

    # Populate metrics
    state.metrics["nodes_expanded"] = state.nodes_expanded
    state.metrics["final_score"] = best_node.score
    state.metrics["time_taken"] = time.time() - state.start_time
    state.metrics["stop_reason"] = state.stop_reason

    print(f"[FINALIZE] Final Answer: {final_answer}")
    return state




def rerank_thoughts(state: GraphState) -> GraphState:
    """Reranks the newly generated thoughts in the frontier using BGE Reranker."""
    if state.cancellation_event and state.cancellation_event.is_set():
        print("[RERANK] Cancellation requested, stopping.")
        return state

    if not state.frontier:
        print("[RERANK] Frontier is empty, nothing to rerank.")
        return state

    if not state.config.use_reranker:
        print("[RERANK] Reranker is disabled in config. Skipping reranking.")
        return state

    print(f"[RERANK] Reranking {len(state.frontier)} thoughts.")

    reranker_instance = BGEReranker(model_name=state.config.reranker_model)
    
    # Get the actual text of the thoughts in the frontier
    thoughts_to_rerank = [state.nodes[node_id].text for node_id in state.frontier]
    
    # The query for reranking is the original task instruction
    query = state.task.instruction
    
    # Perform reranking
    # The reranker returns a list of (document_text, score) tuples, sorted by score
    reranked_results = reranker_instance.rerank(
        query=query,
        documents=thoughts_to_rerank,
        top_n=state.config.reranker_top_n
    )

    # Create a mapping from original thought text to its node_id
    thought_text_to_id = {state.nodes[node_id].text: node_id for node_id in state.frontier}

    # Update the frontier with the reranked (and potentially pruned) nodes
    new_frontier_ids = []
    for text, score in reranked_results:
        node_id = thought_text_to_id.get(text)
        if node_id:
            # Optionally, store the reranker score in the node for debugging/analysis
            state.nodes[node_id].reranker_score = score
            new_frontier_ids.append(node_id)

    state.frontier = new_frontier_ids
    print(f"[RERANK] Frontier after reranking: {len(state.frontier)} nodes (top {state.config.reranker_top_n}).")

    return state

