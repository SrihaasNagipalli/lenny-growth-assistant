"""
Lenny Growth Assistant agent.

This module orchestrates the full request-response cycle:
1. Retrieve relevant transcript chunks via RAG
2. Build a grounded prompt with source context
3. Call the LLM (Claude or Ollama via llm_service)
4. Optionally invoke the Ship30 or Artifact skills
5. Return structured response with sources

The agent uses tool-like routing internally rather than the full
Anthropic agent loop, for predictability and auditability.
"""
import logging
from typing import Optional

from app.services.llm_service import llm_service, SYSTEM_PROMPT
from app.services.rag_service import rag_service
from app.services.ship30_service import generate_ship30_essay
from app.services.artifact_service import generate_artifact
from app.models.schemas import SourceOut

logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """Use the following transcript excerpts from Lenny's Podcast to answer the user's question.

RETRIEVED CONTEXT:
{context}

CONVERSATION HISTORY:
{history}

USER QUESTION: {question}

Answer grounded in the context above. If the context doesn't fully address the question, say so.
Always mention which episode(s) you drew from."""

NO_CONTEXT_RESPONSE = (
    "I searched the indexed transcripts but couldn't find relevant material for your question. "
    "This topic may not be covered in the currently indexed episodes, or the phrasing may differ. "
    "Try rephrasing, or check if more transcripts need to be ingested."
)


class LennyAgent:
    async def run(
        self,
        user_message: str,
        conversation_history: list[dict],
        generate_ship30: bool = False,
        generate_artifact_type: Optional[str] = None,
    ) -> dict:
        """
        Main agent entry point.
        Returns: {content, sources, artifact, provider, model}
        """
        # Step 1: Retrieve relevant chunks
        sources, chunks = rag_service.retrieve_with_text(user_message)

        # Step 2: Check if we have usable context
        if not sources:
            logger.info("No RAG context found for: %.80s", user_message)
            return {
                "content": NO_CONTEXT_RESPONSE,
                "sources": [],
                "artifact": None,
                "provider": llm_service.current_provider,
                "model": llm_service.current_model,
            }

        # Step 3: Build context string
        context = rag_service.build_context(sources, chunks)

        # Step 4: Build message history for LLM
        history_text = self._format_history(conversation_history[-8:])

        # Step 5: Route to skill or standard chat
        if generate_ship30:
            content = await generate_ship30_essay(
                topic=user_message,
                sources=sources,
                context_chunks=chunks,
                conversation_history=conversation_history,
            )
            artifact = {"type": "markdown", "content": content}
        else:
            # Standard grounded answer
            rag_prompt = RAG_PROMPT_TEMPLATE.format(
                context=context,
                history=history_text,
                question=user_message,
            )
            messages = [{"role": "user", "content": rag_prompt}]
            content = await llm_service.chat(messages=messages, system=SYSTEM_PROMPT)
            artifact = None

        # Step 6: Optionally also generate artifact
        if generate_artifact_type and not generate_ship30:
            artifact = await generate_artifact(
                request=user_message,
                artifact_type=generate_artifact_type,
                sources=sources,
                context_chunks=chunks,
                conversation_history=conversation_history,
            )

        return {
            "content": content,
            "sources": [s.model_dump() for s in sources],
            "artifact": artifact,
            "provider": llm_service.current_provider,
            "model": llm_service.current_model,
        }

    def _format_history(self, history: list[dict]) -> str:
        if not history:
            return "No prior conversation."
        lines = []
        for m in history:
            role = m.get("role", "user").capitalize()
            content = m.get("content", "")[:400]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


lenny_agent = LennyAgent()
