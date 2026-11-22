import io

import pytest
from docx import Document as DocxDocument

from app.rag.fusion import reciprocal_rank_fusion
from app.rag.loaders import chunk_pages, extract_pages


def test_txt_extraction_strips_nul_bytes():
    pages = extract_pages("notes.txt", b"hello\x00 world")
    assert pages == [(None, "hello world")]


def test_docx_extraction_includes_paragraphs_and_tables():
    doc = DocxDocument()
    doc.add_paragraph("Vacation policy")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Days"
    table.rows[0].cells[1].text = "25"
    buf = io.BytesIO()
    doc.save(buf)

    [(page, text)] = extract_pages("policy.docx", buf.getvalue())
    assert page is None
    assert "Vacation policy" in text
    assert "Days | 25" in text


def test_unsupported_extension_raises():
    with pytest.raises(ValueError):
        extract_pages("malware.exe", b"MZ")


def test_chunking_keeps_page_numbers_and_overlap():
    text = " ".join(f"word{i}" for i in range(400))
    chunks = chunk_pages([(3, text)], chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 1
    assert all(c.page == 3 for c in chunks)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(len(c.content) <= 200 for c in chunks)


def test_rrf_prefers_hits_found_by_both_searches():
    a = {"chunk_id": 1}
    b = {"chunk_id": 2}
    c = {"chunk_id": 3}
    fused = reciprocal_rank_fusion([[a, b], [c, b]], limit=3)
    assert fused[0]["chunk_id"] == 2  # appears in both lists
    assert {h["chunk_id"] for h in fused} == {1, 2, 3}
