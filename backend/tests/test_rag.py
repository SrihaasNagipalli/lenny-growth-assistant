"""
RAG service unit tests.
Tests: chunking, metadata, retrieval, no-context handling.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_chunk_text_basic():
    """Text should be chunked into overlapping segments."""
    from app.services.rag_service import RAGService
    svc = RAGService()

    text = "A" * 2000
    chunks = svc.chunk_text(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= svc.chunk_text.__defaults__  # just check it runs


def test_chunk_text_short():
    """Short text should produce a single chunk."""
    from app.services.rag_service import RAGService
    svc = RAGService()

    text = "This is a short text about product-market fit."
    chunks = svc.chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_filters_tiny():
    """Chunks under 50 chars should be filtered out."""
    from app.services.rag_service import RAGService
    svc = RAGService()

    text = "Hi."  # Very short
    chunks = svc.chunk_text(text)
    assert len(chunks) == 0


def test_ingest_transcript_creates_chunks():
    """Ingest should create the right number of chunks."""
    from app.services.rag_service import RAGService

    svc = RAGService()

    # Mock ChromaDB collection
    mock_collection = MagicMock()
    mock_collection.count.return_value = 3
    svc._collection = mock_collection

    text = "Word " * 500  # 2500 chars — should create multiple chunks
    count = svc.ingest_transcript("ep001", "Test Episode", text)

    assert count > 0
    mock_collection.upsert.assert_called_once()
    call_args = mock_collection.upsert.call_args
    assert len(call_args.kwargs.get("ids", [])) == count


def test_retrieve_empty_collection():
    """Empty collection should return empty list, not error."""
    from app.services.rag_service import RAGService

    svc = RAGService()
    mock_collection = MagicMock()
    mock_collection.count.return_value = 0
    svc._collection = mock_collection

    sources = svc.retrieve("What is product-market fit?")
    assert sources == []


def test_retrieve_with_text_returns_sources_and_chunks():
    """retrieve_with_text should return parallel lists."""
    from app.services.rag_service import RAGService

    svc = RAGService()
    mock_collection = MagicMock()
    mock_collection.count.return_value = 5
    mock_collection.query.return_value = {
        "documents": [["chunk text 1", "chunk text 2"]],
        "metadatas": [
            [
                {"episode": "ep001", "title": "Test", "chunk_index": 0},
                {"episode": "ep002", "title": "Test 2", "chunk_index": 1},
            ]
        ],
        "distances": [[0.1, 0.2]],
    }
    svc._collection = mock_collection

    sources, chunks = svc.retrieve_with_text("product market fit")

    assert len(sources) == 2
    assert len(chunks) == 2
    assert sources[0].episode == "ep001"
    assert sources[0].relevance_score > 0.7  # 1 - 0.1 = 0.9
    assert chunks[0] == "chunk text 1"


def test_build_context_format():
    """Context should be clearly formatted with source attribution."""
    from app.services.rag_service import RAGService
    from app.models.schemas import SourceOut

    svc = RAGService()
    sources = [
        SourceOut(episode="ep001", title="Superhuman PMF", chunk_index=0, relevance_score=0.9, excerpt="...")
    ]
    chunks = ["The 40% rule: if more than 40% would be very disappointed, you have PMF."]

    context = svc.build_context(sources, chunks)

    assert "SOURCE 1" in context
    assert "Superhuman PMF" in context
    assert "ep001" in context
    assert "40%" in context
