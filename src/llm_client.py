import logging
import os

from types import SimpleNamespace
from typing import Any
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings


logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


class DummyLLM:
    """Fallback LLM usado quando não há chave de API disponível.

    Fornece uma interface compatível com o mínimo esperado pelo código
    (methd invoke e with_structured_output).
    """

    def __init__(self, model: str = "dummy", temperature: float = 0.0):
        self.model = model
        self.temperature = temperature

    def invoke(self, _prompt: str) -> SimpleNamespace:
        # Retorna um objeto com atributo `content` com uma resposta vazia em JSON.
        logger.warning(
            "DummyLLM invoked: returning empty proposal. Set GEMINI_API_KEY to enable real LLM."
        )
        return SimpleNamespace(content="[]")

    def with_structured_output(self, model_cls: Any):
        class Structured:
            def invoke(self, _prompt: str):
                # Instancia um objeto de saída estruturada com valores neutros.
                try:
                    return model_cls(
                        progress=0.0,
                        promise=0.0,
                        confidence=0.0,
                        justification="Fallback: LLM not configured",
                    )
                except Exception:
                    # Se model_cls não for um Pydantic BaseModel ou não aceitar estes campos,
                    # simplesmente retornar um objeto simples com atributos padrão.
                    return SimpleNamespace(
                        progress=0.0,
                        promise=0.0,
                        confidence=0.0,
                        justification="Fallback: LLM not configured",
                    )

        return Structured()


class DummyEmbeddings:
    def __init__(self, model: str = "dummy"):
        self.model = model

    def embed(self, texts):
        # Retorna vetores zerados compatíveis com o número de textos requisitados.
        import numpy as np

        if isinstance(texts, str):
            texts = [texts]
        dim = 1
        return [np.zeros(dim) for _ in texts]


def get_chat_llm(
    model: str = "gemini-2.5-flash",
    temperature: float = 0.0,
    google_api_key: Optional[str] = None,
):
    key = google_api_key or GEMINI_API_KEY
    if not key:
        logger.warning(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) not set. Using DummyLLM as fallback."
        )
        return DummyLLM(model=model, temperature=temperature)
    return ChatGoogleGenerativeAI(
        model=model, temperature=temperature, google_api_key=key
    )


def get_embeddings(
    model: str = "gemini-embedding-001", google_api_key: Optional[str] = None
):
    key = google_api_key or GEMINI_API_KEY
    if not key:
        logger.warning(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) not set. Using DummyEmbeddings as fallback."
        )
        return DummyEmbeddings(model=model)
    return GoogleGenerativeAIEmbeddings(model=model, google_api_key=key)  # type: ignore[arg-type]
