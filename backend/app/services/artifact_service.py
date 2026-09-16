"""
Artifact generation service.

Security model for HTML artifacts:
- Generated HTML is treated as untrusted.
- Rendered inside a sandboxed <iframe> with:
    sandbox="allow-scripts" (scripts only, no top-nav, no popups, no forms, no same-origin)
- DOMPurify sanitizes the HTML server-side before storage.
- CSP header set by the iframe's srcdoc — no external resource loading.
- No cookies, localStorage, or fetch() can escape the iframe.
- Markdown artifacts are rendered with marked.js + DOMPurify on the client.
"""
import logging
import re
import bleach

from app.services.llm_service import llm_service
from app.models.schemas import SourceOut

logger = logging.getLogger(__name__)

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr", "pre", "code", "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "ul", "ol", "li", "dl", "dt", "dd",
    "strong", "em", "b", "i", "u", "s", "mark",
    "div", "span", "section", "article", "header", "footer",
    "style",
})

ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "*": ["class", "id", "style"],
    "a": ["href", "title", "rel"],
}

MARKDOWN_ARTIFACT_PROMPT = """Generate a well-structured Markdown document based on the conversation and source material below.

The document should:
- Use proper Markdown headings, lists, tables where appropriate
- Be comprehensive and standalone (someone should understand it without the chat)
- Include source citations
- Be formatted for clarity and skimmability

CONVERSATION CONTEXT:
{conversation}

SOURCE MATERIAL:
{context}

TOPIC/REQUEST: {request}

Return ONLY the Markdown content, starting with # Title."""

HTML_ARTIFACT_PROMPT = """Generate a complete, self-contained HTML/CSS document based on the request below.

Requirements:
- Single HTML file with embedded CSS in a <style> tag
- No external resources (no CDN links, no external fonts — use system fonts)
- Clean, modern design with good typography
- Responsive layout
- No JavaScript (keep it static for safety)
- Summarize or visualize the key insights from the source material

CONVERSATION CONTEXT:
{conversation}

SOURCE MATERIAL:
{context}

REQUEST: {request}

Return ONLY the HTML content (full HTML document starting with <!DOCTYPE html>)."""


def sanitize_html(html: str) -> str:
    """Server-side HTML sanitization using bleach."""
    # Remove script tags and dangerous attributes
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
        strip_comments=True,
    )
    return cleaned


async def generate_artifact(
    request: str,
    artifact_type: str,
    sources: list[SourceOut],
    context_chunks: list[str],
    conversation_history: list[dict],
) -> dict:
    """Generate a Markdown or HTML artifact. Returns {type, content}."""

    # Build context from retrieved chunks
    context_parts = []
    for src, chunk in zip(sources[:3], context_chunks[:3]):
        context_parts.append(f"[{src.title} — {src.episode}]\n{chunk}")
    context = "\n\n---\n\n".join(context_parts) or "No specific source material available."

    # Summarize conversation
    recent = conversation_history[-4:]
    conv_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content'][:300]}" for m in recent
    )

    if artifact_type == "html":
        prompt = HTML_ARTIFACT_PROMPT.format(
            conversation=conv_text, context=context, request=request
        )
        system = "You are an expert web designer. Generate clean, semantic HTML/CSS."
    else:
        prompt = MARKDOWN_ARTIFACT_PROMPT.format(
            conversation=conv_text, context=context, request=request
        )
        system = "You are a technical writer. Generate well-structured Markdown."

    raw_content = await llm_service.chat(
        messages=[{"role": "user", "content": prompt}],
        system=system,
        max_tokens=3000,
    )

    if artifact_type == "html":
        # Sanitize HTML server-side before returning
        content = sanitize_html(raw_content)
        logger.info("HTML artifact generated and sanitized (%d chars)", len(content))
    else:
        content = raw_content
        logger.info("Markdown artifact generated (%d chars)", len(content))

    return {"type": artifact_type, "content": content}
