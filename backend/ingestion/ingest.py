"""
Transcript ingestion pipeline.

Usage:
    python -m ingestion.ingest                    # ingest all files in TRANSCRIPTS_DIR
    python -m ingestion.ingest --file path.txt    # ingest a single file
    python -m ingestion.ingest --clear            # clear and re-ingest

Transcript format expected:
    - Plain text .txt files
    - Filename convention: <episode_id>_<title_slug>.txt  (e.g., ep123_how_superhuman_grew.txt)
    - Or any .txt file — episode_id derived from filename

Traceability:
    Each chunk stored in ChromaDB carries metadata:
    {episode, title, chunk_index, source_file, char_start}
    so every retrieved answer can be traced to its exact source location.
"""
import argparse
import asyncio
import logging
import sys
import re
from pathlib import Path

# Ensure backend root is on the path when run as module
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.rag_service import rag_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_filename(path: Path) -> tuple[str, str]:
    """Extract (episode_id, title) from filename."""
    stem = path.stem
    # Try pattern: ep123_title_slug or 123_title_slug
    match = re.match(r"^(ep)?(\d+)[-_](.+)$", stem, re.IGNORECASE)
    if match:
        ep_num = match.group(2)
        title = match.group(3).replace("_", " ").replace("-", " ").title()
        return f"ep{ep_num}", title
    # Fallback: use full stem as episode ID
    return stem, stem.replace("_", " ").replace("-", " ").title()


def ingest_file(path: Path) -> int:
    """Ingest a single transcript file. Returns chunks added."""
    episode_id, title = parse_filename(path)
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        logger.warning("Empty file: %s — skipping", path)
        return 0
    logger.info("Ingesting: %s | episode=%s | title=%s | chars=%d",
                path.name, episode_id, title, len(text))
    count = rag_service.ingest_transcript(
        episode_id=episode_id,
        title=title,
        text=text,
        metadata={"source_file": path.name},
    )
    return count


def ingest_all(transcripts_dir: str) -> int:
    """Ingest all .txt files in the directory."""
    dir_path = Path(transcripts_dir)
    if not dir_path.exists():
        logger.error("Transcripts directory not found: %s", transcripts_dir)
        return 0

    files = list(dir_path.glob("*.txt")) + list(dir_path.glob("*.md"))
    if not files:
        logger.warning("No .txt or .md files found in %s", transcripts_dir)
        return 0

    total = 0
    for f in sorted(files):
        try:
            total += ingest_file(f)
        except Exception as e:
            logger.error("Failed to ingest %s: %s", f.name, e)

    logger.info("Ingestion complete. Total chunks: %d | Files: %d", total, len(files))
    return total


def main():
    parser = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcripts into ChromaDB")
    parser.add_argument("--file", type=str, help="Ingest a single file")
    parser.add_argument("--dir", type=str, default=settings.TRANSCRIPTS_DIR,
                        help="Directory of transcripts")
    parser.add_argument("--clear", action="store_true", help="Clear collection before ingesting")
    args = parser.parse_args()

    if args.clear:
        try:
            client = rag_service._get_client()
            client.delete_collection(settings.CHROMA_COLLECTION)
            rag_service._collection = None
            logger.info("Collection cleared")
        except Exception as e:
            logger.warning("Could not clear collection: %s", e)

    if args.file:
        count = ingest_file(Path(args.file))
        print(f"Ingested {count} chunks from {args.file}")
    else:
        count = ingest_all(args.dir)
        print(f"Ingested {count} total chunks from {args.dir}")


if __name__ == "__main__":
    main()
