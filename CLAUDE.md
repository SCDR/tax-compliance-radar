# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tax Compliance Radar - An AI-powered tax compliance assistant focused on Thailand VAT. Monorepo with backend (FastAPI) and frontend (React).

## Architecture

### Backend Stack
- **Framework**: FastAPI + uv (package manager)
- **Database**: SQLite (app.db) via SQLAlchemy
- **Vector DB**: ChromaDB for regulation embeddings storage
- **LLM**: Ollama with Qwen3:8b (fallback: llama3.2, qwen2.5)
- **Embeddings**: qwen3-embedding:0.6b (1024 dimensions)

### Key Architecture Layers
```
backend/src/tax_compliance_radar/
├── main.py              # FastAPI app entrypoint
├── config.py            # Settings (LLM config, paths, disclaimer)
├── api/                 # API routers
│   ├── qa_router.py     # Q&A endpoints (/api/v1/qa)
│   └── audit_router.py  # Audit endpoints (/api/v1/audit)
├── services/            # Business logic
│   ├── llm_service.py   # Ollama integration, JSON parsing, fallbacks
│   ├── qa_service.py    # Question answering with RAG
│   ├── audit_service.py # Audit analysis logic
│   ├── compliance_rules.py # Compliance rule definitions
│   └── db.py            # Database initialization
├── database/            # Data layer
│   ├── regulation_loader.py # Load and chunk regulations
│   ├── init_chroma.py   # ChromaDB setup
│   └── init_db.py       # SQLite setup
└── models/              # Pydantic schemas
```

### Frontend
- React + Vite
- Simple SPA for Q&A interface

## Common Commands

### Backend (run from `backend/` directory)

**Initialize everything**:
```bash
bash scripts/init_all.sh    # Create data dirs, init DB, load regulations
```

**Start server**:
```bash
bash scripts/start.sh       # Runs uvicorn on port 8000
```

**Run tests**:
```bash
uv run pytest -q                      # All tests
uv run pytest tests/unit/services/    # Specific test directory
uv run pytest tests/unit/services/test_llm_service.py  # Single test file
```

**Test dependencies**:
```bash
uv run python scripts/test_ollama.py      # Verify Ollama connection
uv run python scripts/test_embeddings.py  # Verify embedding generation
```

### Frontend (run from `frontend/` directory)
```bash
npm install
npm run dev          # Starts dev server
```

## Key Configuration

All settings in [backend/src/tax_compliance_radar/config.py](backend/src/tax_compliance_radar/config.py):
- Default LLM model: `qwen3:8b`
- Embedding model: `qwen3-embedding:0.6b`
- Chroma collection: `thailand_vat_regulations`
- Data stored in `backend/data/`

## Data Flow

1. **Initialization**: `scripts/load_regulations.py` loads markdown files, chunks them, generates embeddings, stores in ChromaDB
2. **Q&A Flow**: User query → embedding generation → Chroma similarity search → LLM prompt with context → JSON response
3. **Audit Flow**: Transaction/entity data → compliance rule matching → LLM analysis → risk assessment

## Important Notes

- Ollama must be running locally on port 11434 for LLM features
- All LLM responses use structured JSON output (temperature: 0.1 for deterministic output)
- Disclaimer text is automatically appended to all responses
- Environment variable `TCR_ENV` controls development/production behavior (default: "development")
