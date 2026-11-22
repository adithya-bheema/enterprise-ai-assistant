"""Ingestion pipeline: extract -> chunk -> embed -> store. Runs as a background task."""

import logging

from ..config import settings
from ..db import SessionLocal
from ..models import Chunk, Document
from .embeddings import get_embeddings
from .loaders import chunk_pages, extract_pages

logger = logging.getLogger(__name__)
EMBED_BATCH = 32


def ingest_document(document_id: int, filename: str, data: bytes) -> None:
    with SessionLocal() as db:
        try:
            pages = extract_pages(filename, data)
            chunks = chunk_pages(pages)
            if not chunks:
                raise ValueError("No extractable text found (scanned PDF? empty file?)")

            embeddings = get_embeddings()
            for start in range(0, len(chunks), EMBED_BATCH):
                batch = chunks[start : start + EMBED_BATCH]
                vectors = embeddings.embed_documents([c.content for c in batch])
                if vectors and len(vectors[0]) != settings.embedding_dim:
                    raise ValueError(
                        f"Embedding size {len(vectors[0])} does not match "
                        f"EMBEDDING_DIM={settings.embedding_dim}. Fix the env var and "
                        "recreate the chunks table."
                    )
                db.add_all(
                    Chunk(
                        document_id=document_id,
                        chunk_index=c.index,
                        page=c.page,
                        content=c.content,
                        embedding=v,
                    )
                    for c, v in zip(batch, vectors)
                )

            doc = db.get(Document, document_id)
            doc.status = "ready"
            doc.chunk_count = len(chunks)
            db.commit()
        except Exception as exc:  # noqa: BLE001 - surface any failure on the document
            logger.exception("Ingestion failed for document %s", document_id)
            db.rollback()
            doc = db.get(Document, document_id)
            if doc is not None:
                doc.status = "failed"
                doc.error = str(exc)[:500]
                db.commit()
