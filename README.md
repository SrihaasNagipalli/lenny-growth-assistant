# The Lenny Growth Assistant

An AI-powered conversational web application that turns Lenny Rachitsky's podcast transcripts into a reliable internal knowledge assistant. Ask complex product and growth questions, generate Ship 30 for 30 essays, and create rendered Markdown/HTML artifacts — all grounded in real transcript content.

---

## Architecture Overview

```
┌──────────────┐     HTTP      ┌──────────────────┐     ┌─────────────┐
│  React UI    │◄──────────────►  FastAPI Backend  │◄────►  PostgreSQL  │
│  (Vite)      │               │  (Python 3.12)   │     │  Sessions   │
└──────────────┘               └────────┬─────────┘     └─────────────┘
                                         │
                              ┌──────────┴──────────┐
                              │    Agent Layer       │
                              │    lenny_agent.py    │
                              └──────────┬──────────┘
                    ┌──────────────────┬─┴────────────────────┐
                    │                  │                       │
             ┌──────┴──────┐   ┌───────┴──────┐    ┌─────────┴──────┐
             │  LLM Service │   │  RAG Service  │    │  Skills Layer  │
             │  (Claude or  │   │  (ChromaDB)   │    │  Ship30/       │
             │   Ollama)    │   └──────────────┘    │  Artifact Gen  │
             └─────────────┘                        └────────────────┘
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker Desktop | 4.x+ | For one-command startup |
| Python | 3.12+ | For local dev |
| Node.js | 20+ | For frontend dev |
| Ollama | Latest | For local LLM demo |

---

## Quick Start (Docker Compose — Recommended)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd Oogway_Assignment

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY or configure LLM_PROVIDER=ollama

# 3. Fetch/create sample transcripts
cd backend
python -m ingestion.fetch_transcripts --samples-only
cd ..

# 4. Start everything
docker compose up --build

# 5. Ingest transcripts into ChromaDB
docker compose exec backend python -m ingestion.ingest

# 6. Open the app
open http://localhost:3000
```

The API docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Local Development (No Docker)

### Backend

```bash
cd backend

# Create virtualenv
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example ../.env
# Edit .env with your settings

# Start PostgreSQL (or use Supabase/Railway — update DATABASE_URL in .env)
# If using local Postgres:
# docker run -d -e POSTGRES_USER=lenny -e POSTGRES_PASSWORD=lenny_pass -e POSTGRES_DB=lenny_db -p 5432:5432 postgres:16-alpine

# Create sample transcripts
python -m ingestion.fetch_transcripts --samples-only
python -m ingestion.ingest

# Start the backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `anthropic` | `anthropic` or `ollama` |
| `ANTHROPIC_API_KEY` | If using Anthropic | — | From console.anthropic.com |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Claude model ID |
| `OLLAMA_BASE_URL` | If using Ollama | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | If using Ollama | `llama3.2` | Model pulled in Ollama |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | Async PostgreSQL URL |
| `CHROMA_PERSIST_DIR` | No | `./data/chroma` | ChromaDB storage path |
| `RAG_TOP_K` | No | `5` | Chunks retrieved per query |
| `TRANSCRIPTS_DIR` | No | `./data/transcripts` | Where .txt transcripts live |

---

## Local Ollama Setup

```bash
# 1. Install Ollama from https://ollama.ai

# 2. Pull a model (pick one that fits your RAM)
ollama pull llama3.2           # ~2GB, fast, recommended
ollama pull mistral            # ~4GB, good quality
ollama pull llama3.1:8b        # ~5GB, excellent quality

# 3. Pull embedding model
ollama pull nomic-embed-text

# 4. Start Ollama server
ollama serve

# 5. Set in .env
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=llama3.2
```

---

## Cloud Model Setup (Anthropic)

```bash
# 1. Get your API key from https://console.anthropic.com/
# 2. In .env:
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-sonnet-4-6
```

---

## Ingesting Transcripts

```bash
# Fetch from GitHub (requires internet)
python -m ingestion.fetch_transcripts --limit 30

# Create sample transcripts (no network needed)
python -m ingestion.fetch_transcripts --samples-only

# Ingest all transcripts in TRANSCRIPTS_DIR
python -m ingestion.ingest

# Ingest a single file
python -m ingestion.ingest --file /path/to/transcript.txt

# Re-index from scratch
python -m ingestion.ingest --clear
```

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Cannot connect to Ollama` | Ollama not running | Run `ollama serve` |
| `Invalid Anthropic API key` | Wrong key in .env | Check ANTHROPIC_API_KEY |
| `Collection is empty` | No transcripts ingested | Run `python -m ingestion.ingest` |
| `DB health check failed` | PostgreSQL not running | Check `docker compose ps` |
| `CORS error in browser` | Wrong CORS_ORIGINS | Add `http://localhost:3000` to .env CORS_ORIGINS |
| Artifact viewer blank | HTML parse error | Check browser console for iframe errors |

---

## Project Structure

```
Oogway_Assignment/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, lifecycle
│   │   ├── config.py         # Settings with LLM toggle
│   │   ├── models/           # SQLAlchemy models + Pydantic schemas
│   │   ├── routes/           # API endpoints (health, sessions, chat)
│   │   ├── services/         # LLM, RAG, Artifact, Ship30 services
│   │   └── agents/           # Lenny agent orchestrator
│   ├── ingestion/            # Transcript fetch & ingest pipeline
│   ├── tests/                # Pytest test suite
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/       # Chat, ArtifactViewer, SessionList, MessageBubble
│       ├── hooks/            # useChat state management
│       └── api/              # Typed API client
├── data/
│   └── transcripts/          # .txt transcript files (gitignored)
├── agent_transcripts/        # Coding agent session logs
├── docker-compose.yml
├── .env.example
├── PRD.md
├── design.md
└── architecture.md
```

---

## Manual UI Test Plan

1. **New session**: Click "New chat" → verify a session appears in sidebar
2. **Send message**: Type a growth question → verify response with source citations
3. **Follow-up**: Ask a follow-up → verify context is maintained
4. **Ship 30 essay**: Check "Ship 30 for 30 Essay" → send → verify ~1250 word essay with headings
5. **Markdown artifact**: Check "Generate Artifact" + "Markdown" → send → click "View Markdown Artifact"
6. **HTML artifact**: Check "Generate Artifact" + "HTML" → verify iframe renders with security note
7. **Empty retrieval**: Ask something outside transcripts → verify graceful "no data" message
8. **Session history**: Select a previous session → verify messages reload
9. **Delete session**: Hover session → click delete → verify it disappears
10. **Provider badge**: Verify provider/model shows in the header
11. **Responsive**: Resize to mobile width → verify layout stacks correctly
