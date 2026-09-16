"""
Persistence tests — session and message CRUD logic.
These use mocked DB sessions to avoid requiring a live PostgreSQL instance in CI.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


def make_fake_session(title="Test", user_metadata=None):
    s = MagicMock()
    s.id = uuid.uuid4()
    s.title = title
    s.user_metadata = user_metadata or {}
    s.created_at = datetime.now(timezone.utc)
    s.updated_at = datetime.now(timezone.utc)
    return s


def make_fake_message(session_id=None, role="user", content="Hello"):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.session_id = session_id or uuid.uuid4()
    m.role = role
    m.content = content
    m.sources = []
    m.artifact = None
    m.llm_provider = "anthropic"
    m.llm_model = "claude-sonnet-4-6"
    m.created_at = datetime.now(timezone.utc)
    return m


@pytest.mark.asyncio
async def test_session_schema_serialization():
    """SessionOut should serialize UUID and datetime fields correctly."""
    from app.models.schemas import SessionOut

    session_data = {
        "id": uuid.uuid4(),
        "title": "Growth Strategy",
        "user_metadata": {"source": "web"},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    out = SessionOut(**session_data)
    serialized = out.model_dump()

    assert isinstance(serialized["id"], uuid.UUID)
    assert serialized["title"] == "Growth Strategy"


@pytest.mark.asyncio
async def test_message_schema_with_sources():
    """MessageOut should handle sources and artifact fields."""
    from app.models.schemas import MessageOut, SourceOut, ArtifactOut

    sources = [
        SourceOut(
            episode="ep001",
            title="Superhuman PMF",
            chunk_index=0,
            relevance_score=0.92,
            excerpt="The 40% rule..."
        )
    ]
    artifact = ArtifactOut(type="markdown", content="# Essay\n\nContent here...")

    msg = MessageOut(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        role="assistant",
        content="Based on Lenny's podcast...",
        sources=sources,
        artifact=artifact,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        created_at=datetime.now(timezone.utc),
    )

    assert len(msg.sources) == 1
    assert msg.sources[0].episode == "ep001"
    assert msg.artifact.type == "markdown"


@pytest.mark.asyncio
async def test_chat_request_validation():
    """ChatRequest should validate message length and artifact_type."""
    from pydantic import ValidationError
    from app.models.schemas import ChatRequest

    # Valid request
    req = ChatRequest(message="What is product-market fit?")
    assert req.message == "What is product-market fit?"
    assert req.generate_artifact is False

    # Empty message should fail
    with pytest.raises(ValidationError):
        ChatRequest(message="")

    # Invalid artifact_type should fail
    with pytest.raises(ValidationError):
        ChatRequest(message="Generate a report", artifact_type="pdf")


@pytest.mark.asyncio
async def test_session_list_schema():
    """SessionList should correctly count total."""
    from app.models.schemas import SessionList, SessionOut

    sessions = [
        SessionOut(
            id=uuid.uuid4(),
            title=f"Session {i}",
            user_metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        for i in range(3)
    ]
    session_list = SessionList(sessions=sessions, total=10)
    assert session_list.total == 10
    assert len(session_list.sessions) == 3


@pytest.mark.asyncio
async def test_source_out_relevance_score_bounds():
    """Relevance scores should be between 0 and 1."""
    from app.services.rag_service import RAGService

    svc = RAGService()
    mock_collection = MagicMock()
    mock_collection.count.return_value = 3
    mock_collection.query.return_value = {
        "documents": [["chunk1"]],
        "metadatas": [[{"episode": "ep001", "title": "Test", "chunk_index": 0}]],
        "distances": [[0.0]],  # perfect match
    }
    svc._collection = mock_collection

    sources = svc.retrieve("test query")
    assert sources[0].relevance_score == 1.0

    # Test with max distance
    mock_collection.query.return_value["distances"] = [[1.0]]
    svc._collection = mock_collection
    sources = svc.retrieve("test query")
    assert sources[0].relevance_score == 0.0
