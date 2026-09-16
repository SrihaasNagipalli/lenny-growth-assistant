#!/bin/bash
set -e

# Auto-ingest transcripts if ChromaDB is empty
echo "Checking ChromaDB..."
python -c "
import os, sys
sys.path.insert(0, '/app')
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
from app.services.rag_service import rag_service
count = rag_service.get_doc_count()
print(f'ChromaDB has {count} chunks')
sys.exit(0 if count > 0 else 1)
" && echo "ChromaDB already populated, skipping ingest." || {
    echo "ChromaDB empty — running ingestion..."
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
        TOKENIZERS_PARALLELISM=false python -m ingestion.ingest
    echo "Ingestion complete."
}

# Start the FastAPI server
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
