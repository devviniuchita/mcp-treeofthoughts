
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

try:
    from rerankers import Reranker
    RERANKER_AVAILABLE = True
except ImportError:
    logger.warning("A biblioteca \'rerankers\' ou suas dependências (e.g., transformers, torch) não estão instaladas. O reranking será desabilitado.")
    RERANKER_AVAILABLE = False

class BGEReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.reranker = None
        if RERANKER_AVAILABLE:
            try:
                self.reranker = Reranker(model_name)
                logger.info(f"BGE Reranker \'{model_name}\' inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao inicializar BGE Reranker \'{model_name}\': {e}. O reranking será desabilitado.")
                self.reranker = None
        
    def rerank(self, query: str, documents: List[str], top_n: int = 3) -> List[Tuple[str, float]]:
        if not self.reranker:
            logger.warning("Reranker não está disponível. Retornando documentos originais (limitado por top_n).")
            # Fallback: return top_n documents without reranking
            return [(doc, 0.0) for doc in documents[:top_n]]

        if not documents:
            return []

        try:
            # The reranker.rank method expects query and documents as separate arguments
            results = self.reranker.rank(query, documents)
            
            reranked_documents = []
            for i, r in enumerate(results):
                if i >= top_n:
                    break
                # Ensure we use the original document text based on index
                reranked_documents.append((documents[r.index], r.score))

            return reranked_documents
        except Exception as e:
            logger.error(f"Erro durante o reranking: {e}. Retornando documentos originais (limitado por top_n).")
            # Fallback: return top_n documents without reranking
            return [(doc, 0.0) for doc in documents[:top_n]]

