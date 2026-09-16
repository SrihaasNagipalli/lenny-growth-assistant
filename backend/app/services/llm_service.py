"""
LLM abstraction supporting Anthropic Claude, OpenRouter, and Ollama.
Switch provider via LLM_PROVIDER env var without changing application code.
"""
import logging
from typing import AsyncIterator, Optional
import anthropic
import httpx

from app.config import settings, LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are The Lenny Growth Assistant — an expert on product management and growth strategy,
grounded exclusively in Lenny Rachitsky's podcast transcripts.

Rules:
1. Answer ONLY from the provided transcript context. Do not invent facts.
2. Always cite the source episode(s) you used.
3. If the transcripts don't support an answer, say so clearly: "Based on the available transcripts, I don't have information about X. You might find the answer in episodes not yet indexed."
4. For follow-up questions, maintain context from the conversation.
5. Be concise, actionable, and specific — like a great PM advisor would be.
"""


class LLMService:
    def __init__(self):
        self._anthropic_client: Optional[anthropic.AsyncAnthropic] = None

    @property
    def current_provider(self) -> str:
        return settings.LLM_PROVIDER.value

    @property
    def current_model(self) -> str:
        if settings.LLM_PROVIDER == LLMProvider.ANTHROPIC:
            return settings.ANTHROPIC_MODEL
        if settings.LLM_PROVIDER == LLMProvider.OPENROUTER:
            return settings.OPENROUTER_MODEL
        return settings.OLLAMA_MODEL

    def _get_anthropic_client(self) -> anthropic.AsyncAnthropic:
        if not self._anthropic_client:
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is not configured")
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
        return self._anthropic_client

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> str:
        """Single-turn chat completion."""
        system_text = system or SYSTEM_PROMPT

        if settings.LLM_PROVIDER == LLMProvider.ANTHROPIC:
            return await self._anthropic_chat(messages, system_text, max_tokens)
        if settings.LLM_PROVIDER == LLMProvider.OPENROUTER:
            return await self._openrouter_chat(messages, system_text, max_tokens)
        return await self._ollama_chat(messages, system_text, max_tokens)

    async def _anthropic_chat(
        self, messages: list[dict], system: str, max_tokens: int
    ) -> str:
        client = self._get_anthropic_client()
        try:
            response = await client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.AuthenticationError:
            raise ValueError("Invalid Anthropic API key")
        except anthropic.RateLimitError:
            raise RuntimeError("Anthropic rate limit exceeded — try again shortly")
        except anthropic.APITimeoutError:
            raise TimeoutError("Anthropic API timed out")
        except Exception as e:
            logger.exception("Anthropic error: %s", e)
            raise

    async def _openrouter_chat(
        self, messages: list[dict], system: str, max_tokens: int
    ) -> str:
        """Call OpenRouter's OpenAI-compatible chat completions endpoint."""
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not configured")

        # OpenAI format: system message is first in the messages list
        openai_messages = [{"role": "system", "content": system}] + messages

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lenny-growth-frontend.onrender.com",
            "X-Title": "The Lenny Growth Assistant",
        }
        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if r.status_code == 401:
                    raise ValueError("Invalid OpenRouter API key")
                if r.status_code == 429:
                    raise RuntimeError("OpenRouter rate limit exceeded — try again shortly")
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
        except httpx.ConnectError:
            raise RuntimeError("Cannot connect to OpenRouter API")
        except httpx.TimeoutException:
            raise TimeoutError("OpenRouter request timed out (>120s)")
        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            logger.exception("OpenRouter error: %s", e)
            raise

    async def _ollama_chat(
        self, messages: list[dict], system: str, max_tokens: int
    ) -> str:
        """Call Ollama's /api/chat endpoint."""
        ollama_messages = [{"role": "system", "content": system}] + messages
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": ollama_messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload
                )
                r.raise_for_status()
                return r.json()["message"]["content"]
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. "
                "Ensure Ollama is running: `ollama serve`"
            )
        except httpx.TimeoutException:
            raise TimeoutError("Ollama request timed out (>120s)")
        except Exception as e:
            logger.exception("Ollama error: %s", e)
            raise

    async def check_ollama_health(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def get_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for retrieval. Uses Ollama embed or falls back to sentence-transformers."""
        if settings.LLM_PROVIDER == LLMProvider.OLLAMA:
            return await self._ollama_embed(text)
        return await self._local_embed(text)

    async def _ollama_embed(self, text: str) -> list[float]:
        payload = {"model": settings.OLLAMA_EMBED_MODEL, "prompt": text}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings", json=payload
            )
            r.raise_for_status()
            return r.json()["embedding"]

    async def _local_embed(self, text: str) -> list[float]:
        """Lightweight sentence-transformers embedding (CPU-only fallback)."""
        try:
            from sentence_transformers import SentenceTransformer
            import asyncio

            model = SentenceTransformer("all-MiniLM-L6-v2")
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, model.encode, text)
            return embedding.tolist()
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. Install it or use Ollama for embeddings."
            )


llm_service = LLMService()
