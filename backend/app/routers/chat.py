import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent.runtime import get_graph
from ..db import get_db
from ..deps import get_current_user
from ..models import Conversation, Message, User
from ..schemas import ChatRequest, ChatResponse, ConversationOut, MessageOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

HISTORY_MESSAGES = 6


def _own_conversation(db: Session, conversation_id: int, user: User) -> Conversation:
    convo = db.get(Conversation, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise HTTPException(404, detail="Conversation not found")
    return convo


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if body.conversation_id:
        convo = _own_conversation(db, body.conversation_id, user)
    else:
        convo = Conversation(user_id=user.id, title=body.question.strip()[:80])
        db.add(convo)
        db.flush()

    recent = db.scalars(
        select(Message)
        .where(Message.conversation_id == convo.id)
        .order_by(Message.id.desc())
        .limit(HISTORY_MESSAGES)
    ).all()
    history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

    try:
        graph = get_graph()
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc

    try:
        result = graph.invoke(
            {"question": body.question, "history": history, "attempts": 0},
            config={"configurable": {"db": db, "user_id": user.id}},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Agent run failed")
        raise HTTPException(
            502, detail="The AI service failed to answer. Please try again."
        ) from None

    db.add_all(
        [
            Message(conversation_id=convo.id, role="user", content=body.question),
            Message(
                conversation_id=convo.id,
                role="assistant",
                content=result["answer"],
                citations=result["citations"],
            ),
        ]
    )
    db.commit()
    return ChatResponse(
        conversation_id=convo.id, answer=result["answer"], citations=result["citations"]
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def conversation_messages(
    conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _own_conversation(db, conversation_id, user).messages


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    db.delete(_own_conversation(db, conversation_id, user))
    db.commit()
