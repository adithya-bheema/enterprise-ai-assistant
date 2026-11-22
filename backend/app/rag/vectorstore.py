"""pgvector-backed search. Every query is filtered by document visibility."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..models import Chunk, Document


def _visible_to(user_id: int):
    return or_(Document.visibility == "org", Document.owner_id == user_id)


def _hit(chunk: Chunk, filename: str, score: float) -> dict:
    return {
        "chunk_id": chunk.id,
        "document_id": chunk.document_id,
        "filename": filename,
        "page": chunk.page,
        "content": chunk.content,
        "score": score,
    }


def vector_search(db: Session, query_vec: list[float], user_id: int, k: int) -> list[dict]:
    distance = Chunk.embedding.cosine_distance(query_vec).label("distance")
    stmt = (
        select(Chunk, Document.filename, distance)
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.status == "ready", _visible_to(user_id))
        .order_by(distance)
        .limit(k)
    )
    return [_hit(chunk, fn, 1.0 - float(dist)) for chunk, fn, dist in db.execute(stmt).all()]


def keyword_search(db: Session, query: str, user_id: int, k: int) -> list[dict]:
    tsv = func.to_tsvector("english", Chunk.content)
    tsq = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank_cd(tsv, tsq).label("rank")
    stmt = (
        select(Chunk, Document.filename, rank)
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.status == "ready", _visible_to(user_id), tsv.op("@@")(tsq))
        .order_by(rank.desc())
        .limit(k)
    )
    return [_hit(chunk, fn, float(r)) for chunk, fn, r in db.execute(stmt).all()]
