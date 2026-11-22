"""Hybrid retrieval: pgvector cosine search + Postgres full-text, fused with RRF."""

from functools import lru_cache

from sqlalchemy.orm import Session

from ..config import settings
from .embeddings import get_embeddings
from .fusion import reciprocal_rank_fusion
from .vectorstore import keyword_search, vector_search


@lru_cache
def _cross_encoder():
    from sentence_transformers import CrossEncoder  # requirements-hf.txt

    return CrossEncoder(settings.reranker_model)


def rerank(query: str, hits: list[dict]) -> list[dict]:
    if not hits:
        return hits
    scores = _cross_encoder().predict([(query, h["content"]) for h in hits])
    ranked = sorted(zip(hits, scores), key=lambda pair: float(pair[1]), reverse=True)
    return [{**hit, "rerank": float(score)} for hit, score in ranked]


def hybrid_retrieve(query: str, db: Session, user_id: int) -> list[dict]:
    query_vec = get_embeddings().embed_query(query)
    semantic = vector_search(db, query_vec, user_id, settings.fetch_k)
    lexical = keyword_search(db, query, user_id, settings.fetch_k)
    fused = reciprocal_rank_fusion([semantic, lexical], limit=settings.fetch_k)
    if settings.reranker_enabled:
        fused = rerank(query, fused)
    return fused[: settings.top_k]
