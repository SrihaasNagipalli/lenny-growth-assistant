# Design Document
## The Lenny Growth Assistant

---

## 1. UI/UX Principles

### 1.1 Core Design Principles

**1. Grounding first, not generation theater**  
Every answer must cite its source. The UI makes sources impossible to miss — they appear as badges below each message with episode name, ID, and relevance score. Users never have to wonder "where did this come from?"

**2. Minimize cognitive overhead**  
The user comes with a question, not with a desire to configure AI systems. The LLM provider toggle, artifact generation, and Ship 30 skill are all opt-in via small checkboxes — visible but unobtrusive. Default behavior is just "ask a question."

**3. Trust through transparency**  
- Provider badge in the top bar shows exactly which model answered  
- Source citations include relevance scores  
- HTML artifacts show a security notice in amber  
- Empty retrieval explains *why* it can't answer, not just "I don't know"

**4. Chat-first, artifact-secondary**  
The main panel is always the conversation. The artifact viewer opens as a right panel without pushing the chat away. Users can close it instantly. This mirrors how Claude Artifacts works — exploration doesn't interrupt the dialogue.

**5. Keyboard-first power users**  
Enter sends. Shift+Enter for new lines. All interactive elements have accessible labels. The input auto-focuses on new session.

---

## 2. Information Architecture

```
App
├── Sidebar (left, 256px)
│   ├── Logo + tagline
│   ├── New Chat button
│   └── Session list (newest first)
│       └── Session row (title, date, delete on hover)
│
└── Main Area (flex-fill)
    ├── Provider badge bar (top, shows LLM + indexed chunks)
    ├── Chat area (scrollable)
    │   ├── Empty state (logo + suggested prompts)
    │   └── Message list
    │       ├── User message bubble
    │       └── Assistant message bubble
    │           ├── Rendered Markdown
    │           ├── Source badges (episode, relevance, excerpt)
    │           └── "View Artifact" button (if artifact exists)
    ├── Input area (bottom, sticky)
    │   ├── Skill toggles (Ship 30, Artifact + type)
    │   └── Textarea + Send button
    │
    └── Artifact Panel (right, 480px, optional)
        ├── Header (type badge, Copy, Download, Close)
        ├── Security notice (HTML only)
        └── Content (Markdown prose or sandboxed iframe)
```

---

## 3. Key Interaction States

| State | UI Behavior |
|-------|-------------|
| **Loading** | Typing indicator (3 bouncing dots), send button shows spinner, input disabled |
| **Error** | Red alert box below message list, session remains active |
| **Empty session** | Centered empty state with logo and 5 suggested prompts |
| **No retrieval results** | Assistant message explains no matching transcripts found |
| **Artifact open** | Right panel slides in; chat remains fully readable |
| **Session delete (hover)** | Red trash icon appears on hover; click requires no confirmation (recoverable by refresh — future: undo toast) |
| **Copy success** | Button text changes to "✓ Copied" for 2 seconds |

---

## 4. Component Design

### 4.1 MessageBubble

Two variants based on role:

| Property | User | Assistant |
|----------|------|-----------|
| Alignment | Right-aligned | Left-aligned |
| Background | Brand blue (#4361ee) | White with border |
| Text color | White | Gray-800 |
| Corner rounding | All except top-right | All except top-left |
| Content | Plain text | Rendered Markdown |
| Sources | None | Source badge list |
| Artifact | None | "View Artifact" button |

### 4.2 ArtifactViewer

The artifact viewer balances rendering richness with security:

**Markdown artifacts:**
- Rendered with `marked.js` (CommonMark + GFM)
- Sanitized with `DOMPurify` (strips scripts, event handlers)
- Full prose styling (headings, code blocks, tables, blockquotes)
- White background, comfortable line height

**HTML artifacts:**
- Rendered in `<iframe srcDoc>` with `sandbox="allow-scripts"`
- No `allow-same-origin` — iframe gets unique opaque origin
- CSP meta tag injected into `<head>`: `default-src 'none'`
- Cannot access parent cookies, localStorage, or make external requests
- Amber security notice visible above the iframe
- Server-side bleach sanitization before storage

### 4.3 SessionList

- Shows last 20 sessions, newest first
- Session title = first 60 chars of first user message
- Hover reveals delete button
- Active session highlighted in gray-700

---

## 5. Responsive Behavior

| Breakpoint | Behavior |
|-----------|----------|
| Desktop (>1024px) | Full three-column layout: sidebar + chat + artifact panel |
| Tablet (768–1024px) | Sidebar collapses to icon strip; artifact panel overlays |
| Mobile (<768px) | Chat full-width; sidebar hidden by default (hamburger); artifact panel is modal |

The current implementation targets desktop primarily. Tailwind's responsive utilities (`sm:`, `md:`, `lg:`) are used throughout. Mobile-first breakpoints are defined but the layout is desktop-optimized for the demo.

---

## 6. Accessibility Considerations

- All buttons have `aria-label` where icon-only
- Color is never the sole differentiator (source badges use text labels, not just color)
- Focus ring preserved on all interactive elements
- Typing indicator uses `aria-live="polite"` (implicit via DOM update)
- Textarea has descriptive placeholder text
- Error messages are not ephemeral — they remain visible until the next successful response
- Contrast ratios: primary text (#111827) on white = 16.1:1 (AAA); white on #4361ee ≈ 4.9:1 (AA)

---

## 7. Design Decisions and Rationale

| Decision | Alternative Considered | Rationale |
|---------|----------------------|-----------|
| Artifact viewer as side panel | Modal overlay | Preserves ability to reference the conversation while reading the artifact |
| Skill toggles as checkboxes | Separate "mode" selector | Composable: can combine Ship 30 + Artifact generation |
| Sources below assistant messages | Tooltip on hover | Always visible — grounding is a core feature, not an afterthought |
| No streaming | SSE streaming | Reduces backend complexity for MVP; easier to persist complete messages |
| Tailwind CSS | Component library | Zero runtime cost, full control, no vendor lock-in |
| Gray-900 sidebar | Light sidebar | Matches convention (VS Code, Slack) for reduced visual noise alongside the chat |
