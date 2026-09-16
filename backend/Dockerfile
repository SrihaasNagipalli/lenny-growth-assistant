FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# Install CPU-only torch first to avoid pulling ~2GB of CUDA libraries
RUN pip install --no-cache-dir --retries 10 --timeout 300 torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --retries 10 --timeout 300 -r requirements.txt

# Pre-download SentenceTransformer model used by rag_service at build time
# so containers can run fully offline (HF_HUB_OFFLINE=1 at runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', device='cpu').encode(['warmup'])"

# Copy source
COPY . .

# Create data directories
RUN mkdir -p data/transcripts data/chroma

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["/app/start.sh"]
