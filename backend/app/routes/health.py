import logging
from fastapi import APIRouter
from sqlalchemy import text

from app.models.database import AsyncSessionLocal
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.models.schemas import HealthResponse
from app.config import settings, LLMProvider

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check — DB, Chroma, and LLM provider."""

    # Check DB
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error("DB health check failed: %s", e)

    # Check Chroma
    chroma_ok = rag_service.is_available()

    # Check Ollama if it's the active provider
    ollama_ok = None
    if settings.LLM_PROVIDER == LLMProvider.OLLAMA:
        ollama_ok = await llm_service.check_ollama_health()

    return HealthResponse(
        status="ok" if (db_ok and chroma_ok) else "degraded",
        version=settings.APP_VERSION,
        llm_provider=llm_service.current_provider,
        llm_model=llm_service.current_model,
        db_connected=db_ok,
        chroma_connected=chroma_ok,
        ollama_available=ollama_ok,
    )


@router.get("/config")
async def get_config():
    """Return current LLM configuration."""
    return {
        "llm_provider": llm_service.current_provider,
        "llm_model": llm_service.current_model,
        "available_providers": ["anthropic", "ollama"],
        "rag_top_k": settings.RAG_TOP_K,
        "indexed_chunks": rag_service.get_doc_count(),
    }
