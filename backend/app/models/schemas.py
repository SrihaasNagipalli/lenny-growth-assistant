from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ── Session schemas ────────────────────────────────────────────────
class SessionCreate(BaseModel):
    title: Optional[str] = None
    user_metadata: dict[str, Any] = {}


class SessionOut(BaseModel):
    id: UUID
    title: Optional[str]
    user_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionList(BaseModel):
    sessions: list[SessionOut]
    total: int


# ── Message schemas ────────────────────────────────────────────────
class ArtifactOut(BaseModel):
    type: str  # "markdown" | "html"
    content: str


class SourceOut(BaseModel):
    episode: str
    title: str
    chunk_index: int
    relevance_score: float
    excerpt: str


class MessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    sources: list[SourceOut] = []
    artifact: Optional[ArtifactOut] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat request/response ──────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    generate_artifact: bool = False
    artifact_type: Optional[str] = Field(default=None, pattern="^(markdown|html)$")
    generate_ship30: bool = False


class ChatResponse(BaseModel):
    session_id: UUID
    message: MessageOut
    provider: str
    model: str


# ── Health ─────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    llm_model: str
    db_connected: bool
    chroma_connected: bool
    ollama_available: Optional[bool] = None


# ── Config ─────────────────────────────────────────────────────────
class ConfigResponse(BaseModel):
    llm_provider: str
    llm_model: str
    available_providers: list[str]
    rag_top_k: int


class ProviderSwitchRequest(BaseModel):
    provider: str = Field(..., pattern="^(anthropic|ollama)$")


# ── Error ──────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
