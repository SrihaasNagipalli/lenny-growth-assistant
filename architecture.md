# Architecture Document
## The Lenny Growth Assistant

---

## 1. System Overview

```
                          ┌─────────────────────────────────────┐
                          │          Docker Compose              │
                          │                                      │
  Browser  ──HTTP──►  ┌──┴───────┐     ┌────────────────────┐   │
                       │ React    │     │   FastAPI Backend   │   │
                       │ Frontend │◄────►  (Python 3.12)     │   │
                       │ :3000    │     │  :8000              │   │
                       └──────────┘     └───────┬────────────┘   │
                                                │                 │
                               ┌────────────────┼──────────┐     │
                               │                │          │     │
                         ┌─────┴────┐   ┌───────┴──┐  ┌───┴──┐  │
                         │PostgreSQL│   │ ChromaDB  │  │Ollama│  │
                         │  :5432   │   │(embedded) │  │:11434│  │
                         └──────────┘   └───────────┘  └──────┘  │
                          sessions/                               │
                          messages                                │
                                        └─────────────────────────┘
```

---

## 2. Database Schema

### 2.1 PostgreSQL Tables

```sql
-- Sessions table
CREATE TABLE sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title        VARCHAR(255),
    user_metadata JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- Messages table
CREATE TABLE messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role         VARCHAR(20) NOT NULL,  -- 'user' | 'assistant'
    content      TEXT NOT NULL,
    sources      JSONB DEFAULT '[]',   -- [{episode, title, chunk_index, relevance_score, excerpt}]
    artifact     JSONB,                -- {type: 'markdown'|'html', content: str}
    llm_provider VARCHAR(50),
    llm_model    VARCHAR(100),
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
```

### 2.2 ChromaDB Schema (Vector Store)

Each document chunk is stored as:
```json
{
  "id":      "ep001_chunk_3",
  "document": "The fundamental question is: how disappointed...",
  "metadata": {
    "episode":      "ep001",
    "title":        "How Superhuman Built Product-Market Fit",
    "chunk_index":  3,
    "source_file":  "ep001_superhuman_pmf.txt"
  }
}
```

Collection: `lenny_transcripts` | Metric: cosine | Embedding: sentence-transformers `all-MiniLM-L6-v2`

---

## 3. API Endpoints

### Health & Configuration

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Comprehensive health check | None |
| `GET` | `/config` | Current LLM provider and settings | None |

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sessions` | Create a new session |
| `GET` | `/api/v1/sessions` | List sessions (paginated) |
| `GET` | `/api/v1/sessions/{id}` | Get session details |
| `DELETE` | `/api/v1/sessions/{id}` | Delete session + messages |
| `GET` | `/api/v1/sessions/{id}/messages` | Get all messages in session |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/sessions/{id}/chat` | Send message, get grounded response |

#### Chat Request Schema
```json
{
  "message": "string (1-10000 chars)",
  "generate_artifact": false,
  "artifact_type": "markdown | html | null",
  "generate_ship30": false
}
```

#### Chat Response Schema
```json
{
  "session_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "...",
    "sources": [
      {
        "episode": "ep001",
        "title": "How Superhuman Built PMF",
        "chunk_index": 3,
        "relevance_score": 0.92,
        "excerpt": "The fundamental question..."
      }
    ],
    "artifact": { "type": "markdown", "content": "# Essay..." },
    "llm_provider": "anthropic",
    "llm_model": "claude-sonnet-4-6",
    "created_at": "2026-09-15T10:00:00Z"
  },
  "provider": "anthropic",
  "model": "claude-sonnet-4-6"
}
```

---

## 4. Component Boundaries

```
backend/app/
├── main.py           — FastAPI app init, CORS, error handlers, lifecycle
├── config.py         — Pydantic Settings, LLM_PROVIDER toggle
│
├── models/
│   ├── database.py   — SQLAlchemy ORM models, engine, session factory
│   └── schemas.py    — Pydantic request/response models (contracts)
│
├── routes/
│   ├── health.py     — GET /health, GET /config
│   ├── sessions.py   — Session CRUD
│   └── chat.py       — POST /{session_id}/chat (wires agent → DB)
│
├── services/
│   ├── llm_service.py    — Unified LLM abstraction (Claude + Ollama)
│   ├── rag_service.py    — ChromaDB queries, chunking, context building
│   ├── ship30_service.py — Ship 30 for 30 essay generation skill
│   └── artifact_service.py — Markdown/HTML artifact generation + sanitization
│
└── agents/
    └── lenny_agent.py    — Orchestrator: RAG → skill routing → LLM call
```

---

## 5. Ingestion/Retrieval Flow

```
Ingest (one-time / periodic)
─────────────────────────────
.txt files in /data/transcripts/
         │
         ▼
fetch_transcripts.py
  Downloads from GitHub or creates samples
         │
         ▼
ingest.py
  1. Read file → extract episode_id, title from filename
  2. chunk_text() → 800-char overlapping chunks with 100-char overlap
  3. ChromaDB.upsert() → stored with metadata (episode, title, chunk_index)
     [embedding generated by sentence-transformers or Ollama nomic-embed-text]


Query (per request)
─────────────────────────────
user_message
         │
         ▼
rag_service.retrieve_with_text(query, top_k=5)
  ChromaDB.query(query_texts=[msg], n_results=5)
  → returns docs + metadata + cosine distances
         │
         ▼
sources (list[SourceOut]) + chunks (list[str])
         │
         ▼
rag_service.build_context(sources, chunks)
  → "SOURCE 1: Title (episode: epXXX)\n<chunk text>"
         │
         ▼
lenny_agent.run() → llm_service.chat(messages, system)
         │
         ▼
response with citations
```

---

## 6. Agent Routing

```
lenny_agent.run(user_message, history, generate_ship30, artifact_type)
     │
     ├── RAG retrieval → sources, chunks
     │
     ├── if no sources:
     │     return NO_CONTEXT_RESPONSE
     │
     ├── if generate_ship30:
     │     → ship30_service.generate_ship30_essay()
     │       (uses SHIP30_SYSTEM prompt + SHIP30_USER_TEMPLATE)
     │       return essay as artifact {type: markdown, content: ...}
     │
     ├── else (standard chat):
     │     → llm_service.chat(RAG_PROMPT_TEMPLATE, system=SYSTEM_PROMPT)
     │
     └── if artifact_type (markdown/html):
           → artifact_service.generate_artifact()
             (separate LLM call with document-generation prompt)
             → bleach sanitize if HTML
```

---

## 7. LLM Provider Toggle

The toggle is implemented in `config.py` via `LLM_PROVIDER` env var.

```python
class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
```

`llm_service.chat()` dispatches to `_anthropic_chat()` or `_ollama_chat()` based on `settings.LLM_PROVIDER`. No application code outside `llm_service.py` needs to know which provider is active.

**Fallback behavior:**
1. If `LLM_PROVIDER=anthropic` but `ANTHROPIC_API_KEY` is empty → `ValueError` returned as 400 response
2. If `LLM_PROVIDER=ollama` but Ollama is unreachable → `RuntimeError` returned as 503 response with explanation
3. Health endpoint explicitly reports `ollama_available: true/false` so operators can see status at a glance

---

## 8. Security Model

### 8.1 HTML Artifact Rendering

Generated HTML is treated as untrusted user content:

| Layer | Mechanism | What it prevents |
|-------|-----------|-----------------|
| Server-side | `bleach.clean()` with allowlist | Script injection, dangerous attributes |
| Transport | HTTPS (production) | MITM modification |
| Client rendering | `<iframe sandbox="allow-scripts">` | Top-navigation, popups, form submission |
| Origin isolation | No `allow-same-origin` | Cookie/localStorage access from iframe |
| Resource loading | CSP meta: `default-src 'none'` | External image/script/fetch exfiltration |

The iframe can run inline scripts (needed for interactive charts) but cannot reach the parent document's DOM, cookies, or any external origin.

### 8.2 Markdown Rendering

- `marked.js` parses CommonMark + GFM
- `DOMPurify.sanitize()` with `FORBID_TAGS: ['script', 'iframe', 'object', 'embed']`
- Result injected via `dangerouslySetInnerHTML` (safe after DOMPurify)

### 8.3 API Security

- Input validation via Pydantic schemas (message length limit: 10,000 chars)
- Structured error responses — no stack traces exposed in production
- CORS restricted to configured origins
- No secrets in logs (API key filtered from config endpoint)

---

## 9. Deployment Topology

### Local Development
```
Developer machine
├── PostgreSQL (Docker or local)
├── ChromaDB (embedded in backend process)
├── Ollama (native binary, port 11434)
├── Backend (uvicorn, port 8000)
└── Frontend (Vite dev server, port 3000)
```

### Docker Compose (Demo)
```
docker-compose.yml
├── postgres       (postgres:16-alpine)
├── backend        (python:3.12-slim)  — port 8000
└── frontend       (nginx:alpine)       — port 3000, proxies /api → backend
```

Note: Ollama runs on the **host** machine (not in Docker) to access GPU. Backend connects via `host.docker.internal:11434`.

### Production (Recommended)
```
Cloud provider (Railway, Render, Fly.io)
├── Backend service (FastAPI)
├── PostgreSQL (managed, e.g., Supabase)
├── ChromaDB (persistent volume)
└── Frontend (static CDN, e.g., Vercel)
Ollama: not in production; use Anthropic Claude
```

---

## 10. Observability

Structured log fields on every chat request:

```json
{
  "timestamp": "2026-09-15T10:00:00Z",
  "level": "INFO",
  "logger": "app.routes.chat",
  "message": "Chat complete",
  "session_id": "...",
  "provider": "anthropic",
  "sources_found": 4,
  "artifact_type": null
}
```

Error conditions logged with `logger.exception()` (includes stack trace). Health endpoint provides real-time visibility into DB, ChromaDB, and Ollama status.
