import faiss
import numpy as np
from typing import List, Dict, Any, Optional
import os
from src.llm_client import get_embeddings

class SemanticCache:
    def __init__(self, embedding_model_name: str = "gemini-embedding-001", dimension: int = 3072, google_api_key: Optional[str] = None):
        self.embeddings_model = get_embeddings(model=embedding_model_name, google_api_key=google_api_key)
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(self.dimension)  # inner product on normalized vectors = cosine
        self.texts = []
        self.metadata = []

    def _get_embedding(self, text: str) -> np.ndarray:
        raw_embedding = self.embeddings_model.embed_query(text)
        print(f"[DEBUG] Raw embedding type: {type(raw_embedding)}, length: {len(raw_embedding)}")
        vec = np.array(raw_embedding).astype("float32")
        # Ensure the embedding is 1D
        if vec.ndim == 2 and vec.shape[0] == 1:
            vec = vec.flatten()
        elif vec.ndim != 1:
            raise ValueError(f"Unexpected embedding shape: {vec.shape}. Expected 1D array after flattening.")

        if vec.shape[0] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch! Expected {self.dimension}, got {vec.shape[0]} after flattening.")

        # Normalize
        norm = np.linalg.norm(vec)
        if norm == 0:
            return np.zeros(self.dimension, dtype="float32")
        return (vec / norm).astype("float32")

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        embedding = self._get_embedding(text).reshape(1, -1)
        self.index.add(embedding)
        self.texts.append(text)
        self.metadata.append(metadata or {})

    def search(self, query_text: str, k: int = 1, min_score: float = 0.75) -> List[Dict[str, Any]]:
        q = self._get_embedding(query_text).reshape(1, -1)
        scores, indices = self.index.search(q, k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            score = float(scores[0][i])
            # scores are inner product of normalized vectors -> cosine in [-1,1]
            if score >= min_score:
                results.append({"text": self.texts[idx], "metadata": self.metadata[idx], "score": score})
        return results

