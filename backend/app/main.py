import logging
import logging.config
import os
from contextlib import asynccontextmanager

# Limit OpenMP/MKL threads to prevent memory oversubscription during model loading
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.database import create_tables
from app.routes import health, sessions, chat, admin
from app.models.schemas import ErrorResponse

# ── Structured logging ─────────────────────────────────────────────
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifecycle ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("LLM provider: %s | model: %s", settings.LLM_PROVIDER,
                settings.ANTHROPIC_MODEL if settings.LLM_PROVIDER.value == "anthropic" else settings.OLLAMA_MODEL)

    try:
        await create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error("Database init failed: %s — continuing without persistence", e)

    yield

    logger.info("Shutting down")


# ── App ────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered conversational assistant grounded in Lenny's Podcast transcripts",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handlers ──────────────────────────────────────────
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(error="Not found", detail=str(exc.detail)).model_dump(),
    )


@app.exception_handler(500)
async def server_error(request: Request, exc):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            code="INTERNAL_ERROR",
        ).model_dump(),
    )


# ── Routers ────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
