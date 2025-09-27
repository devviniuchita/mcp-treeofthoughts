import os

from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_chat_llm(
    model: str = "gemini-2.5-flash",
    temperature: float = 0.0,
    google_api_key: Optional[str] = None,
):
    key = google_api_key or GEMINI_API_KEY
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) not set. Export it as env var."
        )
    return ChatGoogleGenerativeAI(
        model=model, temperature=temperature, google_api_key=key
    )


def get_embeddings(
    model: str = "gemini-embedding-001", google_api_key: Optional[str] = None
):
    key = google_api_key or GEMINI_API_KEY
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) not set. Export it as env var."
        )
    return GoogleGenerativeAIEmbeddings(model=model, google_api_key=key)
