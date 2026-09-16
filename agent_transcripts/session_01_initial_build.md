# Agent Session 01 — Initial Build
**Date:** 2026-09-15  
**Agent:** Claude Code (claude-sonnet-4-6)  
**Goal:** Scaffold the full project structure and implement core backend

---

## Prompt 1
> Create the folder structure for "The Lenny Growth Assistant" full-stack app. Backend should use FastAPI, agent layer with Anthropic SDK, PostgreSQL for persistence, ChromaDB for vector store, and support both Anthropic Claude and Ollama.

**Agent response:**  
Created directory tree:
```
Oogway_Assignment/
├── backend/app/{models,routes,services,agents}
├── backend/ingestion
├── backend/tests
├── frontend/src/{components,hooks,api}
├── data/transcripts
└── agent_transcripts
```

---

## Prompt 2
> Implement the LLM service abstraction that supports both Anthropic Claude and Ollama without requiring code changes — only an env var toggle.

**Agent first attempt:**
```python
# Initial attempt used requests (synchronous)
import requests

def chat(messages, system=""):
    r = requests.post(OLLAMA_URL, json={...})
```

**Problem identified:** FastAPI runs in an async event loop. Using synchronous `requests` would block the entire server under load.

**Correction:**
```python
# Corrected to use httpx.AsyncClient
async with httpx.AsyncClient(timeout=120.0) as client:
    r = await client.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload)
```

**Lesson learned:** Always use async HTTP clients (httpx, aiohttp) with FastAPI. Synchronous I/O in async routes starves the event loop.

---

## Prompt 3
> Implement ChromaDB RAG service with overlapping chunking and cosine similarity retrieval.

**Agent first attempt:**
```python
# Used fixed-size word splitting
chunks = text.split(' ')
chunks = [' '.join(chunks[i:i+150]) for i in range(0, len(chunks), 150)]
```

**Problem identified:** Word-based chunking ignores sentence boundaries. Chunks often cut mid-sentence, degrading semantic coherence for the embedding model.

**Correction:**
```python
# Character-based with sentence-boundary snapping
def chunk_text(self, text: str) -> list[str]:
    size = settings.RAG_CHUNK_SIZE
    overlap = settings.RAG_CHUNK_OVERLAP
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            last_period = text.rfind(".", start, end)
            if last_period > start + size // 2:
                end = last_period + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
```

**Lesson learned:** Sentence-aware chunking produces more coherent embeddings. The period-snap heuristic is a good balance between simplicity and quality.

---

## Prompt 4
> The health endpoint needs to check ChromaDB availability without crashing if ChromaDB isn't initialized yet.

**Problem:** First attempt called `collection.count()` directly, which throws if the client hasn't been initialized.

**Fix:**
```python
def is_available(self) -> bool:
    try:
        self._get_collection()
        return True
    except Exception:
        return False
```

Wrapped in try/except so health check degrades gracefully.

---

## Prompt 5
> The ingestion script needs to trace every chunk back to its source file and position.

**Agent added metadata fields:**
```python
metadatas = [
    {
        "episode": episode_id,
        "title": title,
        "chunk_index": i,
        "source_file": path.name,  # Added for traceability
    }
    for i in range(len(chunks))
]
```

This allows the API response to include `source_file` in the citation, so a user can go look up the exact transcript.
