from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import Document, User
from ..rag.loaders import SUPPORTED_EXTENSIONS, extension_of
from ..rag.pipeline import ingest_document
from ..schemas import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])


def _out(doc: Document, user: User) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    out.mine = doc.owner_id == user.id
    return out


@router.post("", response_model=DocumentOut, status_code=202)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    visibility: str = Form("org"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filename = file.filename or "upload"
    if extension_of(filename) not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400, detail=f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    if visibility not in {"org", "private"}:
        raise HTTPException(400, detail="visibility must be 'org' or 'private'")

    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, detail=f"File exceeds {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, detail="File is empty")

    doc = Document(
        owner_id=user.id,
        filename=filename[:512],
        content_type=file.content_type or "",
        visibility=visibility,
        status="processing",
    )
    db.add(doc)
    db.commit()
    background.add_task(ingest_document, doc.id, filename, data)
    return _out(doc, user)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Document).order_by(Document.created_at.desc())
    if user.role != "admin":
        stmt = stmt.where(or_(Document.visibility == "org", Document.owner_id == user.id))
    return [_out(d, user) for d in db.scalars(stmt)]


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    doc = db.get(Document, document_id)
    if doc is None or (doc.visibility == "private" and doc.owner_id != user.id and user.role != "admin"):
        raise HTTPException(404, detail="Document not found")
    if doc.owner_id != user.id and user.role != "admin":
        raise HTTPException(403, detail="Only the owner or an admin can delete this document")
    db.delete(doc)
    db.commit()
