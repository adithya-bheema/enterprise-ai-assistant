"""Wires the LangGraph workflow to Gemini and the real database retriever."""

from functools import lru_cache

from langchain_core.runnables import RunnableConfig

from ..config import settings
from ..rag.retrieval import hybrid_retrieve
from .graph import build_graph


def _db_retriever(query: str, config: RunnableConfig) -> list[dict]:
    cfg = config["configurable"]
    return hybrid_retrieve(query, cfg["db"], cfg["user_id"])


@lru_cache
def get_graph():
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=0,
        max_retries=2,
    )
    return build_graph(llm, _db_retriever)
