"""
Ship 30 for 30 essay generation skill.

Writing principles encoded from Ship 30 for 30 methodology:
- ~1,250 words
- One strong, declarative hook sentence (no "I" opener)
- "1 Sentence / 1 Idea" — short sentences, one idea per line
- Skimmable structure: headings, numbered lists, bullets
- Selective bold emphasis on the single most important phrase per section
- Specific, actionable takeaway at the end
- Credibility via concrete examples and data from the source material
- "Obvious to you, amazing to others" — share what insiders know
"""
import logging
from app.services.llm_service import llm_service
from app.models.schemas import SourceOut

logger = logging.getLogger(__name__)

SHIP30_SYSTEM = """You are a world-class digital writer trained in the Ship 30 for 30 methodology.
Your essays are read by 10,000+ product managers who demand actionable insight, not vague advice.

Ship 30 for 30 Core Principles you MUST follow:
1. Hook first: Open with ONE declarative sentence that states the insight immediately. Never start with "I".
2. 1 sentence = 1 idea: Use short sentences. Never pack two ideas into one sentence.
3. Skimmable: Use H2 subheadings, numbered lists, and bullets so a skimmer gets the value in 90 seconds.
4. Bold ONE phrase per section — the single most important thing to remember.
5. Target ~1,250 words. Not 900. Not 1,600.
6. End with a specific, actionable "Here's the takeaway" section.
7. Ground every claim in the source material. Quote or paraphrase real transcript content.
8. Concrete over abstract: Use numbers, names, and specific examples.
9. Never use buzzwords or corporate speak.
10. The reader should finish feeling smarter and ready to do something different.
"""

SHIP30_USER_TEMPLATE = """Write a Ship 30 for 30-style essay on the following topic using ONLY the source material below.

TOPIC: {topic}

SOURCE MATERIAL FROM LENNY'S TRANSCRIPTS:
{context}

CONVERSATION CONTEXT (for continuity):
{conversation_summary}

Requirements:
- Exactly follow Ship 30 for 30 principles
- ~1,250 words
- Use H2 headings (##) for each section
- Bold the single most important phrase in each section using **bold**
- End with a "## The Takeaway" section with 3 specific action items
- Cite the episode source inline like: (Source: {episode_hint})
- Return only the essay content in Markdown format
"""


async def generate_ship30_essay(
    topic: str,
    sources: list[SourceOut],
    context_chunks: list[str],
    conversation_history: list[dict],
) -> str:
    """Generate a Ship 30 for 30 essay grounded in retrieved transcript chunks."""

    if not context_chunks:
        return (
            "## No Source Material Available\n\n"
            "I couldn't find relevant transcript content to support an essay on this topic. "
            "Please try a topic covered in the indexed episodes."
        )

    # Build the context block
    context_parts = []
    for src, chunk in zip(sources, context_chunks):
        context_parts.append(f"**{src.title}** (episode: {src.episode}):\n{chunk}")
    context = "\n\n---\n\n".join(context_parts)

    # Summarize recent conversation (last 3 exchanges)
    recent = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
    conv_summary = "\n".join(
        f"{m['role'].capitalize()}: {m['content'][:200]}..."
        for m in recent
        if m["role"] in ("user", "assistant")
    ) or "No prior conversation."

    episode_hint = sources[0].episode if sources else "Lenny's Podcast"

    prompt = SHIP30_USER_TEMPLATE.format(
        topic=topic,
        context=context,
        conversation_summary=conv_summary,
        episode_hint=episode_hint,
    )

    try:
        essay = await llm_service.chat(
            messages=[{"role": "user", "content": prompt}],
            system=SHIP30_SYSTEM,
            max_tokens=2000,
        )
        logger.info("Ship 30 essay generated for topic: %s", topic[:60])
        return essay
    except Exception as e:
        logger.exception("Ship 30 essay generation failed: %s", e)
        raise
