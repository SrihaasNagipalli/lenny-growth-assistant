"""
RAG service using ChromaDB for vector storage and retrieval.
Transcripts are chunked, embedded, and retrieved at query time.

Embeddings are computed directly via SentenceTransformers and passed
to ChromaDB as pre-computed vectors (bypassing ChromaDB's built-in
embedding function wrappers which have issues in ChromaDB 1.5.x).
"""
import logging
import os
import re
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

# Limit CPU thread oversubscription before any torch/transformers import
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from app.config import settings
from app.models.schemas import SourceOut

logger = logging.getLogger(__name__)

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer model (all-MiniLM-L6-v2)…")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        logger.info("Embedding model ready")
    return _embedding_model


def _embed(texts: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


class RAGService:
    def __init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    def _get_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            # No embedding_function: we pass pre-computed embeddings ourselves.
            # metadata hnsw:space=cosine matches normalize_embeddings=True.
            self._collection = client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def is_available(self) -> bool:
        try:
            self._get_collection()
            return True
        except Exception:
            return False

    def get_doc_count(self) -> int:
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks by character count."""
        size = settings.RAG_CHUNK_SIZE
        overlap = settings.RAG_CHUNK_OVERLAP
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                last_period = text.rfind(".", start, end)
                if last_period > start + size // 2:
                    end = last_period + 1
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = end - overlap
        return [c for c in chunks if len(c) > 50]

    def ingest_transcript(
        self, episode_id: str, title: str, text: str, metadata: Optional[dict] = None
    ) -> int:
        """Chunk, embed, and add a transcript to ChromaDB. Returns chunks added."""
        collection = self._get_collection()
        chunks = self.chunk_text(text)
        if not chunks:
            return 0

        ids = [f"{episode_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "episode": episode_id,
                "title": title,
                "chunk_index": i,
                **(metadata or {}),
            }
            for i in range(len(chunks))
        ]

        # Pre-compute embeddings ourselves — bypasses ChromaDB 1.5.x wrapper bugs
        embeddings = _embed(chunks)

        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Ingested %d chunks for episode: %s", len(chunks), episode_id)
        return len(chunks)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> list[SourceOut]:
        """Retrieve the most relevant chunks for a query."""
        collection = self._get_collection()
        k = top_k or settings.RAG_TOP_K

        if collection.count() == 0:
            logger.warning("ChromaDB collection is empty — no transcripts indexed")
            return []

        query_embedding = _embed([query])[0]

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.exception("ChromaDB query failed: %s", e)
            return []

        sources = []
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(docs, metas, distances):
            relevance = max(0.0, 1.0 - dist)
            sources.append(
                SourceOut(
                    episode=meta.get("episode", "unknown"),
                    title=meta.get("title", "Unknown Episode"),
                    chunk_index=meta.get("chunk_index", 0),
                    relevance_score=round(relevance, 4),
                    excerpt=doc[:300] + ("..." if len(doc) > 300 else ""),
                )
            )

        return sources

    def retrieve_with_text(self, query: str, top_k: Optional[int] = None):
        """Return (sources, full_chunk_texts) for context building."""
        collection = self._get_collection()
        k = top_k or settings.RAG_TOP_K

        if collection.count() == 0:
            return [], []

        query_embedding = _embed([query])[0]

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.exception("ChromaDB query failed: %s", e)
            return [], []

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        sources = []
        for doc, meta, dist in zip(docs, metas, distances):
            relevance = max(0.0, 1.0 - dist)
            sources.append(
                SourceOut(
                    episode=meta.get("episode", "unknown"),
                    title=meta.get("title", "Unknown Episode"),
                    chunk_index=meta.get("chunk_index", 0),
                    relevance_score=round(relevance, 4),
                    excerpt=doc[:300] + ("..." if len(doc) > 300 else ""),
                )
            )

        return sources, docs

    def build_context(self, sources: list[SourceOut], full_chunks: list[str]) -> str:
        """Format retrieved chunks into a context block for the LLM."""
        parts = []
        for i, (src, chunk) in enumerate(zip(sources, full_chunks)):
            parts.append(
                f"[SOURCE {i+1}: {src.title} (episode: {src.episode})]\n{chunk}"
            )
        return "\n\n---\n\n".join(parts)


rag_service = RAGService()
