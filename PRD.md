# Product Requirements Document
## The Lenny Growth Assistant

**Version:** 1.0  
**Author:** Kishore Varma  
**Date:** 2026-09-15  
**Status:** Final

---

## 1. Forward Deployment Brief

### 1.1 User and Problem

**Primary user:** Product managers, growth leads, and startup founders who regularly listen to Lenny's Podcast and want grounded, expert answers about product strategy — without spending hours searching transcripts manually.

**Job to be done:** When facing a product or growth decision (e.g., "how do I think about my North Star Metric?"), the user wants to quickly surface what world-class practitioners said about it on Lenny's Podcast, get a concise synthesized answer, and — optionally — turn that into shareable written content.

**Pain removed:**  
- Searching 300+ podcast episodes manually takes 2–4 hours per question  
- General-purpose LLMs hallucinate expert opinions or attribute them to the wrong people  
- Insights from past episodes are effectively inaccessible once a team scales past 5 people  

### 1.2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Response grounding rate** | ≥90% of answers cite at least one source | Log `sources` field on each assistant message |
| **Session depth** | ≥3 messages per session on average | `COUNT(messages) / COUNT(sessions)` in Postgres |
| **Retrieval latency (P95)** | <500ms for ChromaDB query | Structured log `rag_latency_ms` per request |
| **Onboarding time** | New engineer can run locally in <10 minutes | Follow README cold |

### 1.3 Assumptions

| # | Assumption | Implication |
|---|-----------|-------------|
| 1 | Transcripts are publicly available text | No scraping complex paywalled content |
| 2 | Users are internal team members, not anonymous public | No auth/rate-limiting required for v1 |
| 3 | The primary use case is lookup and generation, not real-time search | Batch ingestion at startup is acceptable |
| 4 | Users accept that Ollama answers are lower quality than Claude answers | Model selection is documented, not hidden |
| 5 | HTML artifacts are decorative, not interactive forms | Sandboxed iframe without `allow-forms` is safe |
| 6 | Postgres and ChromaDB can run on the same machine | No distributed infrastructure needed |

### 1.4 Scope Choices

**Included:**
- Grounded conversational Q&A with source citations
- Session management with independent context per session
- Ship 30 for 30 essay generation skill
- Markdown and HTML artifact generation with in-app viewer
- Dual LLM support: Anthropic Claude (cloud) + Ollama (local)
- Docker Compose one-command deployment
- FastAPI backend with PostgreSQL persistence
- ChromaDB vector store for transcript retrieval

**Intentionally excluded:**
- User authentication / multi-user access control (v2 scope)
- Real-time transcript updates / webhook-based refresh
- Streaming responses (reduces complexity; chunked JSON is sufficient for MVP)
- Transcript audio processing (text transcripts assumed available)
- Fine-tuned model (RAG is more transparent and updateable)
- Multi-modal features (images, tables from transcripts)

**Why these exclusions:** Each excluded feature adds significant complexity and surface area for failure. For a forward-deployment demo, a focused, reliable v1 outperforms a feature-complete but brittle prototype.

### 1.5 Risks and Trade-offs

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Hallucination** | High | Strict system prompt prohibiting out-of-context answers; source citation required |
| **Empty retrieval** | Medium | Graceful fallback message; log all zero-result queries for re-ingestion |
| **Ollama quality gap** | Medium | Documented in UI; Claude recommended for production use |
| **Unsafe HTML rendering** | High | Sandboxed iframe (no allow-same-origin); bleach server-side sanitization; DOMPurify client-side |
| **ChromaDB cold start** | Low | Persistent volume; warning if collection empty |
| **API key leakage** | High | .gitignore for .env; .env.example with no real values |
| **Database unavailability** | Medium | Graceful degradation: app logs warning, returns 503 with explanation |
| **Transcript copyright** | Medium | Using publicly available transcripts; no redistribution in repo |

---

## 2. Product Description

### 2.1 Core User Flows

#### Flow 1: Grounded Q&A
1. User opens app → existing sessions shown in sidebar
2. User clicks "New chat"
3. User types a growth/product question
4. System retrieves top-5 relevant transcript chunks (RAG)
5. LLM generates a grounded answer with inline citations
6. Response shown with source badges (episode, relevance score, excerpt)
7. User can ask follow-up; session context preserved

#### Flow 2: Ship 30 for 30 Essay
1. User checks "Ship 30 for 30 Essay" toggle
2. User types a topic (e.g., "product-market fit frameworks")
3. System retrieves relevant chunks + generates ~1,250-word essay
4. Essay rendered as Markdown artifact in the viewer panel
5. User can copy or download the essay

#### Flow 3: Artifact Generation
1. User checks "Generate Artifact" + selects Markdown or HTML
2. User sends a message
3. System generates a structured document/page based on the conversation
4. Artifact appears in the side panel (rendered, not raw code)
5. For HTML: sandboxed iframe with security notice
6. User can copy raw content or download the file

---

## 3. Acceptance Criteria

| # | Criteria | Verification |
|---|---------|-------------|
| AC-01 | App starts with `docker compose up --build` | Cold start on clean machine |
| AC-02 | New session created on first message | Check Postgres `sessions` table |
| AC-03 | Answer cites at least one source | Verify `sources` array in API response |
| AC-04 | Unknown-topic query returns graceful message | Ask about a topic not in transcripts |
| AC-05 | Ship 30 essay is ≥1,000 words with headings | Word count + markdown parse |
| AC-06 | HTML artifact renders in iframe, not raw code | Visual check in browser |
| AC-07 | Switching LLM_PROVIDER in .env changes model badge in UI | Edit .env, restart backend |
| AC-08 | Deleting a session removes its messages | Check Postgres cascade delete |
| AC-09 | `/health` returns `"status": "ok"` when all services up | GET /health |
| AC-10 | Malformed chat request returns 422 with structured error | POST empty message |

---

## 4. Implementation Plan

### Phase 1: Core Backend (Days 1–2)
- FastAPI app skeleton, config, database models
- ChromaDB setup + transcript ingestion pipeline
- LLM service with provider toggle

### Phase 2: Agent + Skills (Day 3)
- Lenny agent orchestrator
- Ship 30 for 30 skill
- Artifact generation service

### Phase 3: API + Persistence (Day 3–4)
- Session and message endpoints
- Chat endpoint wiring agent to DB

### Phase 4: Frontend (Days 4–5)
- React app with chat UI
- Artifact viewer with security model
- Session management

### Phase 5: Polish + Deployment (Days 5–6)
- Docker Compose
- Tests
- Documentation
