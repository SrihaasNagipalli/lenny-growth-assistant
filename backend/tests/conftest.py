"""Test configuration and fixtures."""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_rag_service():
    """Mock RAG service with sample responses."""
    from app.models.schemas import SourceOut

    sample_sources = [
        SourceOut(
            episode="ep001",
            title="How Superhuman Built Product-Market Fit",
            chunk_index=0,
            relevance_score=0.92,
            excerpt="The fundamental question is: how disappointed would your users be..."
        )
    ]
    sample_chunks = [
        "The fundamental question is: how disappointed would your users be if they could no longer use your product? Survey users and ask them to pick one of four options."
    ]

    with patch("app.services.rag_service.rag_service") as mock:
        mock.retrieve_with_text.return_value = (sample_sources, sample_chunks)
        mock.retrieve.return_value = sample_sources
        mock.build_context.return_value = "Sample context from Lenny's transcripts..."
        mock.is_available.return_value = True
        mock.get_doc_count.return_value = 250
        yield mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    with patch("app.services.llm_service.llm_service") as mock:
        mock.chat = AsyncMock(return_value="This is a grounded answer from Lenny's transcripts. (Source: ep001)")
        mock.current_provider = "anthropic"
        mock.current_model = "claude-sonnet-4-6"
        mock.check_ollama_health = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
async def app_client(mock_db_session, mock_rag_service, mock_llm_service):
    """Test client with mocked dependencies."""
    from app.main import app
    from app.models.database import get_db

    async def override_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
