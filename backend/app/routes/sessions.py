import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.models.database import get_db, Session as DBSession, Message as DBMessage
from app.models.schemas import SessionCreate, SessionOut, SessionList, MessageOut, SourceOut, ArtifactOut

router = APIRouter(prefix="/sessions", tags=["Sessions"])
logger = logging.getLogger(__name__)


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Start a new chat session."""
    session = DBSession(title=body.title, user_metadata=body.user_metadata)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Session created: %s", session.id)
    return session


@router.get("", response_model=SessionList)
async def list_sessions(
    skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    """List all sessions, newest first."""
    total_result = await db.execute(select(func.count()).select_from(DBSession))
    total = total_result.scalar()

    result = await db.execute(
        select(DBSession).order_by(DBSession.created_at.desc()).offset(skip).limit(limit)
    )
    sessions = result.scalars().all()
    return SessionList(sessions=list(sessions), total=total)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await _get_or_404(session_id, db)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await _get_or_404(session_id, db)
    await db.delete(session)
    await db.commit()
    logger.info("Session deleted: %s", session_id)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def get_messages(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full message history for a session."""
    await _get_or_404(session_id, db)
    result = await db.execute(
        select(DBMessage)
        .where(DBMessage.session_id == session_id)
        .order_by(DBMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [_to_message_out(m) for m in messages]


def _to_message_out(m: DBMessage) -> MessageOut:
    sources = [SourceOut(**s) for s in (m.sources or [])]
    artifact = ArtifactOut(**m.artifact) if m.artifact else None
    return MessageOut(
        id=m.id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        sources=sources,
        artifact=artifact,
        llm_provider=m.llm_provider,
        llm_model=m.llm_model,
        created_at=m.created_at,
    )


async def _get_or_404(session_id: UUID, db: AsyncSession) -> DBSession:
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session
