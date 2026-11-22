"""Turn uploaded files into text pages and then into overlapping chunks."""

import io
from dataclasses import dataclass
from pathlib import PurePosixPath

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@dataclass
class ChunkIn:
    index: int
    content: str
    page: int | None = None


def _clean(text: str) -> str:
    # PostgreSQL text columns cannot contain NUL bytes.
    return text.replace("\x00", "").strip()


def extension_of(filename: str) -> str:
    return PurePosixPath(filename.replace("\\", "/")).suffix.lower()


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    """Return [(page_number_or_None, text), ...] for a supported file."""
    ext = extension_of(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext or filename}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = [(i + 1, _clean(p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    elif ext == ".docx":
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text.strip() for cell in row.cells))
        pages = [(None, _clean("\n".join(parts)))]
    else:  # .txt / .md
        pages = [(None, _clean(data.decode("utf-8", errors="replace")))]

    return [(page, text) for page, text in pages if text]


def chunk_pages(
    pages: list[tuple[int | None, str]],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[ChunkIn]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap if chunk_overlap is not None else settings.chunk_overlap,
    )
    chunks: list[ChunkIn] = []
    for page, text in pages:
        for piece in splitter.split_text(text):
            piece = piece.strip()
            if piece:
                chunks.append(ChunkIn(index=len(chunks), content=piece, page=page))
    return chunks
