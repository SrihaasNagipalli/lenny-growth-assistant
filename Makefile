.PHONY: help setup start stop ingest test clean

help:
	@echo "The Lenny Growth Assistant — Make targets"
	@echo ""
	@echo "  make setup    — Copy .env.example, create venv, install deps"
	@echo "  make start    — Start all services via Docker Compose"
	@echo "  make ingest   — Fetch and ingest transcripts into ChromaDB"
	@echo "  make test     — Run backend test suite"
	@echo "  make stop     — Stop Docker Compose services"
	@echo "  make clean    — Remove containers and volumes"

setup:
	cp -n .env.example .env || true
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd frontend && npm install

start:
	docker compose up --build -d

ingest:
	docker compose exec backend python -m ingestion.fetch_transcripts --samples-only
	docker compose exec backend python -m ingestion.ingest

test:
	cd backend && .venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing

stop:
	docker compose down

clean:
	docker compose down -v
	rm -rf data/chroma
