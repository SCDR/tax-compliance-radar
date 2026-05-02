# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tax Compliance Radar - AI-powered multi-country tax compliance assistant. Monorepo with backend (FastAPI) and frontend (React). Supports intelligent compliance Q&A with RAG, multi-country audit analysis, and streaming responses.

## Architecture

### Backend Stack
- **Framework**: FastAPI + uv (package manager)
- **Database**: SQLite (app.db) via SQLAlchemy ORM
- **Vector DB**: ChromaDB for regulation embeddings (RAG)
- **LLM**: Pluggable provider pattern - Ollama (local) or OpenAI-compatible (remote)
- **Embeddings**: Model configurable, default Qwen3-embedding:0.6b (1024 dims)
- **Streaming**: SSE (Server-Sent Events) for real-time token delivery

### Key Architecture Layers

```
backend/src/tax_compliance_radar/
├── main.py                          # FastAPI app, middleware, route registration
├── config.py                        # Environment config, LLM settings
├── api/
│   ├── qa_router.py                # Q&A endpoints (/api/v1/qa/stream)
│   ├── audit_router.py             # Audit SSE endpoint (/api/v1/audit/sse)
│   ├── countries_router.py         # Multi-country config (/api/v1/countries)
│   ├── regulations_router.py       # Regulation retrieval
│   ├── sse.py                      # SSE response streaming logic
│   └── qa_stream.py                # QA stream handler
├── services/
│   ├── llm_service.py              # LLM interface + factory pattern
│   ├── llm_providers/
│   │   ├── base.py                # BaseProvider abstract class
│   │   ├── ollama_provider.py     # Local Ollama integration
│   │   └── openai_compatible_provider.py  # Remote API integration
│   ├── qa_service.py               # RAG-based Q&A logic
│   ├── audit_service.py            # Audit orchestration
│   ├── ai_risk_detector.py         # AI-powered risk assessment
│   ├── embedding_service.py        # Embedding generation
│   └── db.py                       # SQLAlchemy ORM setup
├── database/
│   ├── regulation_loader.py       # Load markdown → chunks → embeddings
│   └── init_chroma.py             # ChromaDB initialization
├── models/
│   └── schemas.py                 # Pydantic models (audit, business fields, etc)
├── registry/
│   ├── base.py                    # Registry abstract base class
│   ├── registry.py                # Country + dimension configuration loader
│   └── countries/                 # (deprecated - now YAML-based)
├── strategies/
│   └── composite.py               # Multi-country orchestration strategy
└── factories/
    └── strategy_factory.py        # Strategy instantiation factory
```

### Frontend Stack
- React + Vite
- Ant Design for UI components
- SSE listener for streaming results
- Dynamic Slogan system with context-aware suggestions
- PDF export (jspdf + html2canvas)

## Streaming Architecture

### SSE Response Pattern (Dual-Layer)
```
result_section: Final confirmed value (data consistency)
    └── overall_summary, country_result, all_risks, all_suggestions, disclaimer

result_token: Fine-grained token stream (real-time UX)
    └── Delta updates (8-char chunks) for incremental rendering
```

### Frontend Slogan System
- **Base Slogans**: 12 general compliance tips
- **Dynamic Business Tips**: 3-4 contextual tips per business type
  - 跨境电商零售: E-commerce tax implications
  - 品牌出海直营: Direct sales complexities (transfer pricing, etc)
  - 外贸综合服务: Export service compliance
- **Multi-Country Bonus**: Additional tips when 2+ countries selected

## Configuration System

### Multi-Country Registry
Located in `backend/data/countries.yaml`:
```yaml
- code: TH
  country_name: Thailand
  flag: 🇹🇭
  tax_type: VAT
  business_fields:
    - name: monthly_turnover
      type: number
      label: "Monthly Turnover (THB)"
  compliance_dimensions:
    - registration_requirements
    - vat_filing
    - reporting_thresholds
```

Loaded at startup via `registry.py`, no code changes needed.

## LLM Provider Factory

`llm_service.py` bridges provider selection:

```python
# Config-driven provider selection
provider = LLMFactory.create(config.LLM_PROVIDER)  # "ollama" or "openai"
response = provider.query(prompt, think_mode=True/False)
```

Auto-fallback if primary provider unavailable.

## Common Commands

### Backend (run from `backend/` directory)

**Initialize everything**:
```bash
bash scripts/init_all.sh    # Create data dirs, init DB, load regulations, build Chroma index
```

**Start server**:
```bash
bash scripts/start.sh       # Runs: uv run uvicorn src.tax_compliance_radar.main:app --reload --port 8000
```

**Run tests**:
```bash
uv run pytest -q                      # All tests
uv run pytest tests/unit/services/    # Specific directory
uv run pytest tests/integration/      # Integration tests
```

**Verify external dependencies**:
```bash
uv run python scripts/test_ollama.py      # Test Ollama connectivity
uv run python scripts/test_embeddings.py  # Test embedding generation
```

### Frontend (run from `frontend/` directory)
```bash
npm install
npm run dev          # Starts dev server (Vite)
npm run build        # Production build
npm run preview      # Preview build
```

## Key Features

### 1. **Streaming Q&A**
- Endpoint: `POST /api/v1/qa/stream`
- Returns: SSE stream with `result_token` events
- Per-character fade-in animation on frontend
- Optional `think_mode` for deeper analysis

### 2. **SSE Audit Results**
- Endpoint: `GET /api/v1/audit/sse/{task_id}`
- Returns: Multi-phase SSE stream
  - Progress indicators during processing
  - Final audit report with structured risk assessment
  - Per-suggestion token streaming for incremental rendering

### 3. **Multi-Country Configuration**
- Endpoint: `GET /api/v1/countries/configs`
- Returns: Dynamic business fields per country
- No hardcoding - YAML-driven config

### 4. **Regulation Retrieval**
- Endpoint: `GET /api/v1/regulations/{filename}`
- Markdown file serving with caching
- Used by frontend for source reference clicks

## Data Flow

1. **Initialization**:
   - `scripts/load_regulations.py`: Parse markdown → chunk → embed → store in Chroma
   - `registry.py`: Load `countries.yaml` config at startup

2. **Q&A Flow**:
   ```
   User Query → Embedding Generation → Chroma Semantic Search 
   → LLM with Retrieved Context + Sources → SSE Token Stream → Frontend Animation
   ```

3. **Audit Flow**:
   ```
   Business Profile + Countries → LLMFactory.create() → MultiCountryAuditStrategy
   → Parallel AI Analysis per Country → Risk Aggregation → SSE Stream → PDF Export
   ```

## Important Notes

- **Ollama**: Must be running on port 11434 (local development)
- **LLM Temperature**: 0.1 for deterministic structured output
- **Think Mode**: Optional flag that may increase response time for deeper reasoning
- **Environment**: `TCR_ENV` (default: "development") controls logging/behavior
- **Streaming**: All audit/QA responses now use SSE + incremental token rendering
- **Disclaimer**: Auto-appended to all responses from config
- **Frontend Caching**: Slogan lists recalculate when business type or country selection changes

## Recent Major Updates (Latest Session)

1. **Dynamic Slogan Carousel** (Frontend)
   - Context-aware Slogan system based on business type and selected countries
   - Auto-rotates every 3.5 seconds with no adjacent repeat prevention
   - Used in both QA and audit result placeholders

2. **SSE Streaming Architecture** (Backend)
   - Dual-layer: `result_section` (final) + `result_token` (incremental)
   - Result_token provides 8-char chunks for real-time display
   - Supports fine-grained animation on frontend

3. **LLM Provider Factory** (Backend)
   - Pluggable provider pattern (Ollama↔OpenAI-compatible)
   - Automatic fallback on connection failure
   - Think mode flag propagation

4. **Multi-Country Config Registry** (Backend)
   - YAML-based country configuration
   - No code changes needed to add new countries
   - Business fields dynamically loaded per country

5. **Audit Result Min-Height** (Frontend)
   - Audit card now has consistent 600px min-height
   - Better layout stability when results are loading

## Testing Strategy

- Unit tests: Core service logic
- Integration tests: API flow validation
- Manual testing: SSE streaming, multi-country flows
- External deps: Ollama, ChromaDB connectivity checks
