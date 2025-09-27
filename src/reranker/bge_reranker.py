import logging
import os

from typing import Any
from typing import List
from typing import Tuple


logger = logging.getLogger(__name__)

Reranker: Any | None = None
RERANKER_AVAILABLE: bool = False

# Permite desabilitar o reranker via variável de ambiente para ambientes
# em que não queremos carregar dependências pesadas (ex: cloud).
if os.getenv("DISABLE_RERANKER", "0") in {"1", "true", "True"}:
    logger.info("DISABLE_RERANKER is set; reranker will remain disabled.")
    RERANKER_AVAILABLE = False


class BGEReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.reranker = None
        # Lazy import: tenta carregar o reranker apenas quando este objeto for
        # instanciado. Assim evitamos importar transformers e outras dependências
        # pesadas durante o startup do servidor.
        global Reranker, RERANKER_AVAILABLE
        if not RERANKER_AVAILABLE:
            try:
                from rerankers import Reranker as _RerankerImpl

                Reranker = _RerankerImpl
                RERANKER_AVAILABLE = True
            except ImportError:
                logger.warning(
                    (
                        "A biblioteca 'rerankers' ou suas dependências (e.g., "
                        "transformers, torch) não estão instaladas. O reranking "
                        "será desabilitado."
                    )
                )
            except BaseException as exc:  # noqa: BLE001
                logger.error(
                    (
                        "Falha inesperada ao inicializar o reranker. "
                        "O reranking será desabilitado."
                    ),
                    exc_info=exc,
                )

        if RERANKER_AVAILABLE and Reranker is not None:
            try:
                self.reranker = Reranker(model_name)
                logger.info(
                    "BGE Reranker '%s' inicializado com sucesso.",
                    model_name,
                )
            except Exception as e:
                logger.error(
                    (
                        "Erro ao inicializar BGE Reranker '%s': %s. "
                        "O reranking será desabilitado."
                    ),
                    model_name,
                    e,
                )
                self.reranker = None
            except BaseException as exc:  # noqa: BLE001
                logger.error(
                    (
                        "Falha crítica ao inicializar o BGE Reranker '%s'. "
                        "O reranking será desabilitado."
                    ),
                    model_name,
                    exc_info=exc,
                )
                self.reranker = None

    def rerank(
        self, query: str, documents: List[str], top_n: int = 3
    ) -> List[Tuple[str, float]]:
        if not self.reranker:
            logger.warning(
                (
                    "Reranker não está disponível. "
                    "Retornando documentos originais (limitado por top_n)."
                )
            )
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
            logger.error(
                (
                    "Erro durante o reranking: %s. "
                    "Retornando documentos originais (limitado por top_n)."
                ),
                e,
            )
            # Fallback: return top_n documents without reranking
            return [(doc, 0.0) for doc in documents[:top_n]]
