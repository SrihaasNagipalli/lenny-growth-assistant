"""Admin endpoints — ingestion and status."""
import asyncio
import gc
import logging
import os
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


class IngestResponse(BaseModel):
    status: str
    total_chunks: int
    files_processed: int
    message: str


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(clear: bool = False):
    """
    Ingest all transcripts into ChromaDB.

    Runs as a child subprocess so PyTorch can safely create threads
    without conflicting with uvicorn's async thread pool.
    """
    # Release the uvicorn process's ChromaDB client before the subprocess opens it.
    rag_service._client = None
    rag_service._collection = None
    gc.collect()

    cmd = [sys.executable, "-m", "ingestion.ingest"]
    if clear:
        cmd.append("--clear")

    env = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }

    logger.info("Starting ingestion subprocess: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd="/app",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode(errors="replace").strip()
    err = stderr.decode(errors="replace").strip()

    if out:
        logger.info("Ingest stdout:\n%s", out[-2000:])
    if err:
        logger.info("Ingest stderr:\n%s", err[-2000:])

    if proc.returncode != 0:
        logger.error("Ingestion subprocess exited %d", proc.returncode)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed (exit {proc.returncode}): {(err or out)[-500:]}",
        )

    count = rag_service.get_doc_count()
    return IngestResponse(
        status="ok",
        total_chunks=count,
        files_processed=-1,
        message=f"Indexed {count} chunks. {out[-200:]}",
    )


@router.get("/status")
async def ingest_status():
    """Return current ChromaDB document count."""
    return {
        "indexed_chunks": rag_service.get_doc_count(),
        "chroma_available": rag_service.is_available(),
        "transcripts_dir": settings.TRANSCRIPTS_DIR,
    }
