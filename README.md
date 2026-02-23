# Resume Job Fit Analyzer

A production-grade, AI-powered skill-graph matching engine that goes beyond keyword matching. Uses transformer-based NER, SBERT embeddings, FAISS vector search, and knowledge graph reasoning to provide explainable resume–job fit scoring.

---

## Architecture

```
app/
├── api/                    # FastAPI route definitions (thin controller layer)
│   └── routes.py
├── core/                   # Cross-cutting concerns
│   ├── config.py           # Pydantic-settings based configuration
│   ├── dependencies.py     # DI providers (lru_cache singletons)
│   ├── exceptions.py       # Domain exception hierarchy
│   └── logging.py          # Structured logging setup
├── graph/                  # Knowledge graph abstraction
│   ├── models.py           # Node/Edge/SkillGraph domain models
│   └── graph_service.py    # Graph construction + similarity scoring
├── ml/
│   ├── embeddings/
│   │   └── sbert_service.py    # Sentence-BERT wrapper with batch support
│   ├── explainability/
│   │   └── explainer.py        # Human-readable match explanations
│   ├── matching/
│   │   ├── pipeline.py         # End-to-end matching orchestrator
│   │   └── scoring_engine.py   # Multi-stage hybrid scoring
│   └── ner/
│       └── skill_extractor.py  # Transformer NER + rule-based fallback
├── models/
│   └── domain.py           # Internal domain data classes
├── schemas/
│   └── resume.py           # Pydantic request/response schemas
├── services/
│   ├── orchestrator.py     # Request lifecycle coordinator
│   ├── resume_parser.py    # PDF/DOCX text extraction
│   └── skill_normalizer.py # Ontology-based skill normalization
├── utils/
│   ├── file_utils.py       # File I/O helpers
│   └── text_cleaning.py    # Text cleaning pipeline
├── vectorstore/
│   └── faiss_store.py      # FAISS HNSW index wrapper
└── main.py                 # FastAPI app factory + lifespan
```
  
## Key Design Decisions

### 1. Hybrid Skill Extraction (NER + Rule-Based)
The transformer NER model (`dslim/bert-base-NER`) handles general entity extraction but misses niche tech terms. A curated lexicon-based fallback catches what the model misses. NER results take priority; rule-based fills gaps. This dual strategy yields higher recall without sacrificing precision.

### 2. FAISS HNSW over IVF
HNSW was chosen over IVF-PQ because:
- No training phase (critical for small skill ontologies of ~100-500 entries)
- Better recall at equivalent latency
- Simpler operational model (no need to retrain clusters)

### 3. Embedding-Based Skill Normalization
Instead of exact string matching, skills are normalized via cosine similarity in SBERT embedding space. This handles synonyms ("JS" → "JavaScript"), abbreviations ("k8s" → "Kubernetes"), and even typos — without maintaining an exhaustive alias table.

### 4. Separating API Schemas from Domain Models
Pydantic `schemas/` define the API contract. `models/domain.py` defines internal dataclasses. This prevents API changes from breaking internal logic and vice versa.

### 5. Neo4j as Optional Enhancement
The graph service computes all metrics in-memory by default. Neo4j integration is available but not required — the system degrades gracefully without it. This allows lightweight local deployment while supporting full graph DB in production.

### 6. Multi-Stage Scoring
Three orthogonal scoring dimensions:
- **Semantic (50%)**: SBERT embedding similarity between skill sets
- **Graph (30%)**: Structural overlap from the knowledge graph (Jaccard + category overlap)
- **Experience (20%)**: Smooth sigmoid-based experience fit curve

Weights are configurable via environment variables.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/upload_resume` | Upload and process a resume (PDF/DOCX) |
| `POST` | `/api/v1/match` | Match a stored resume against a job description |
| `GET`  | `/api/v1/health` | Health check with model status |

## Quick Start
 
### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Run the server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

### Docker

```bash
# Build and run (API only)
docker build -t resume-analyzer .
docker run -p 8000:8000 resume-analyzer

# Full stack with Neo4j, PostgreSQL, Redis
docker-compose up -d
```

### Example Usage

```bash
# Upload a resume
curl -X POST http://localhost:8000/api/v1/upload_resume \
  -F "file=@resume.pdf"

# Match against a job
curl -X POST http://localhost:8000/api/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "res_abc12345_def67890",
    "job_description": {
      "title": "Senior ML Engineer",
      "description": "We are looking for an ML engineer...",
      "required_skills": ["Python", "PyTorch", "Machine Learning", "NLP"],
      "preferred_skills": ["Docker", "Kubernetes", "AWS"],
      "min_experience_years": 3
    }
  }'
```

## Testing

```bash
# Unit + integration tests (no model download required)
pytest tests/ -v -k "not ner"

# Full tests (downloads NER + SBERT models on first run)
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=html
```

## Performance Notes

- **FAISS HNSW**: Sub-millisecond search for ontologies up to ~100K skills
- **SBERT Batch Encoding**: Configurable batch size (default 32) for throughput optimization
- **Lazy Model Loading**: Models load on first request, not at import time
- **Model Pre-loading**: In production mode (`DEBUG=false`), models pre-load at startup
- **Async Endpoints**: All API endpoints are async for I/O concurrency

##  Tech Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI |
| ML Runtime | PyTorch + HuggingFace Transformers |
| Embeddings | Sentence-BERT (all-MiniLM-L6-v2) |
| Vector Search | FAISS (HNSW index) |
| Graph DB | Neo4j (optional, with in-memory fallback) |
| Metadata DB | PostgreSQL (optional) |
| Cache | Redis (optional) |
| Deployment | Docker + Docker Compose |
