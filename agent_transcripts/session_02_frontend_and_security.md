# Agent Session 02 — Frontend & Security
**Date:** 2026-09-15  
**Agent:** Claude Code (claude-sonnet-4-6)  
**Goal:** Build React frontend, implement artifact viewer with security model, fix Ship30 prompt

---

## Prompt 1
> Build the React frontend with a ChatGPT-style layout: sidebar for sessions, main chat area, artifact viewer panel. Use Tailwind CSS.

**Agent first attempt:**
```jsx
// Used create-react-app pattern with webpack
// Added react-router for navigation
```

**Problem identified:** The assignment has no multi-page navigation — it's a single-view chat app. React Router adds 40KB of JS and complexity for zero benefit here.

**Correction:** Removed React Router. Used Vite (faster dev server, native ESM) with simple component composition. Single `App.jsx` manages all state via `useChat` hook.

**Lesson learned:** Resist the impulse to add routing to every React app. Evaluate whether it's actually needed.

---

## Prompt 2
> Implement the ArtifactViewer. HTML artifacts must be safely rendered — treat them as untrusted.

**Agent first attempt:**
```jsx
// Dangerously set innerHTML directly
<div dangerouslySetInnerHTML={{ __html: artifact.content }} />
```

**Problem identified:** This is a critical XSS vulnerability. A malicious artifact could exfiltrate session data, call external APIs, or inject keyloggers.

**Security analysis conducted:**
1. `dangerouslySetInnerHTML` with unsanitized HTML → XSS risk ❌
2. `<iframe src="blob:...">` without sandbox → Same origin, can access parent cookies ❌
3. `<iframe srcDoc>` without sandbox → HTML injected but still no origin isolation ❌
4. `<iframe srcDoc sandbox="allow-scripts">` **without** `allow-same-origin` → **Unique opaque origin, cannot access parent** ✅

**Final implementation:**
```jsx
<iframe
  srcDoc={safeHtml}
  sandbox="allow-scripts"  // scripts run, but no top-nav, no forms, no same-origin
  title="Artifact Preview"
/>
```

Additional layers:
- Server-side: `bleach.clean()` with allowlist before DB storage
- Client-side: CSP meta injected into `<head>` of srcdoc
- Visual: amber warning banner above iframe

**Lesson learned:** Defense in depth. Server sanitization + iframe sandboxing + CSP = three independent layers. Any one layer failing doesn't compromise the user.

---

## Prompt 3
> The Ship 30 for 30 skill needs encoded writing principles, not a one-off prompt.

**Problem with first attempt:**
```python
# Too vague
prompt = f"Write a Ship30 style essay about {topic}"
```

**Correction — encoded all principles explicitly:**
```python
SHIP30_SYSTEM = """
1. Hook first: ONE declarative sentence. Never start with "I".
2. 1 sentence = 1 idea.
3. Skimmable: Use H2 subheadings, numbered lists, bullets.
4. Bold ONE phrase per section.
5. Target ~1,250 words. Not 900. Not 1,600.
6. End with "## The Takeaway" + 3 action items.
7. Ground every claim in source material.
8. Concrete over abstract: numbers, names, examples.
...
"""
```

**Why this matters:** The assignment specifically said "encode principles in the skill rather than relying on an unstructured one-off prompt." Encoding makes the skill consistent and auditable — anyone reading the code can see exactly what writing rules the LLM is following.

---

## Prompt 4
> The chat endpoint needs to gracefully handle when the agent throws TimeoutError vs RuntimeError vs ValueError.

**First attempt:**
```python
try:
    result = await lenny_agent.run(...)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Problem:** All errors become opaque 500s. The client can't tell if the issue is a bad request (fixable by user) vs. Ollama being down (fixable by ops) vs. a real bug.

**Correction:**
```python
except TimeoutError as e:
    raise HTTPException(status_code=504, detail=str(e))  # Gateway timeout
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))  # Bad config (e.g. no API key)
except RuntimeError as e:
    raise HTTPException(status_code=503, detail=str(e))  # Service unavailable (e.g. Ollama down)
except Exception as e:
    logger.exception("Agent error...")
    raise HTTPException(status_code=500, detail="Internal error")  # Generic
```

**Lesson learned:** Typed exception hierarchy maps cleanly to HTTP status codes. Clients (and ops dashboards) need differentiated errors to take the right action.

---

## Prompt 5
> Tests for RAG service — the chunk_text method has a subtle bug with very short text.

**Bug found during test writing:**
```python
# Bug: overlap subtraction can create infinite loop for short text
start = end - overlap  # if text < overlap, start = negative, loop forever
```

**Fix:**
```python
# Chunk loop terminates correctly
while start < len(text):
    end = min(start + size, len(text))
    ...
    chunks.append(...)
    start = end - overlap
    if start >= len(text):  # safety break
        break
```

Wait — actually the condition `while start < len(text)` handles this because `start` will eventually grow beyond `len(text)`. The issue was only for text shorter than `overlap` where `start` becomes negative and `start < len(text)` remains true. Added filtering: chunks must be >50 chars to avoid garbage.

**Lesson learned:** Write the test first, find the edge case, then fix. Test-driven edge case discovery is more reliable than code review for numerical loops.
