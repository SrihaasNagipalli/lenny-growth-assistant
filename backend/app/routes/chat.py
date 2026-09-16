import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db, Session as DBSession, Message as DBMessage
from app.models.schemas import ChatRequest, ChatResponse, MessageOut, SourceOut, ArtifactOut
from app.agents.lenny_agent import lenny_agent
from app.config import settings, LLMProvider

router = APIRouter(prefix="/sessions/{session_id}/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    session_id: UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get a grounded response from the Lenny Growth Assistant."""

    # Verify session exists
    session = await _get_session_or_404(session_id, db)

    # Load conversation history
    history = await _load_history(session_id, db)

    # Store user message
    user_msg = DBMessage(
        session_id=session_id,
        role="user",
        content=body.message,
        llm_provider=settings.LLM_PROVIDER.value,
        llm_model=settings.ANTHROPIC_MODEL if settings.LLM_PROVIDER == LLMProvider.ANTHROPIC else settings.OLLAMA_MODEL,
    )
    db.add(user_msg)
    await db.flush()

    # Run agent
    try:
        result = await lenny_agent.run(
            user_message=body.message,
            conversation_history=history,
            generate_ship30=body.generate_ship30,
            generate_artifact_type=body.artifact_type if body.generate_artifact else None,
        )
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Agent error for session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail="Internal error in agent execution")

    # Store assistant message
    assistant_msg = DBMessage(
        session_id=session_id,
        role="assistant",
        content=result["content"],
        sources=result.get("sources", []),
        artifact=result.get("artifact"),
        llm_provider=result["provider"],
        llm_model=result["model"],
    )
    db.add(assistant_msg)

    # Update session title if first message
    if session.title is None:
        session.title = body.message[:60] + ("..." if len(body.message) > 60 else "")

    await db.commit()
    await db.refresh(assistant_msg)

    # Build response
    sources = [SourceOut(**s) for s in result.get("sources", [])]
    artifact_data = result.get("artifact")
    artifact = ArtifactOut(**artifact_data) if artifact_data else None

    message_out = MessageOut(
        id=assistant_msg.id,
        session_id=session_id,
        role="assistant",
        content=result["content"],
        sources=sources,
        artifact=artifact,
        llm_provider=result["provider"],
        llm_model=result["model"],
        created_at=assistant_msg.created_at,
    )

    logger.info(
        "Chat complete | session=%s | provider=%s | sources=%d",
        session_id, result["provider"], len(sources)
    )

    return ChatResponse(
        session_id=session_id,
        message=message_out,
        provider=result["provider"],
        model=result["model"],
    )


async def _get_session_or_404(session_id: UUID, db: AsyncSession) -> DBSession:
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


async def _load_history(session_id: UUID, db: AsyncSession) -> list[dict]:
    """Load recent messages as dict list for the agent."""
    result = await db.execute(
        select(DBMessage)
        .where(DBMessage.session_id == session_id)
        .order_by(DBMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]
