from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


def init_db() -> None:
    """Create the pgvector extension, tables and indexes (idempotent)."""
    from . import models  # noqa: F401  (register tables on Base.metadata)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        # Full-text index for the keyword half of hybrid search.
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS chunks_fts_idx "
                "ON chunks USING gin (to_tsvector('english', content))"
            )
        )
        # pgvector's HNSW index supports at most 2000 dimensions.
        if settings.embedding_dim <= 2000:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw "
                    "ON chunks USING hnsw (embedding vector_cosine_ops)"
                )
            )
