# PRD Generator

Transform product intent documents into comprehensive PRD artifacts using a guided, phased generation workflow with human-in-the-loop approval gates.

## Features

- **Two-path flow**: Greenfield (new product) or Modernization (existing system)
- **Guided questionnaire**: Dynamic intake form tailored to flow type
- **3-phase generation with HITL gates**: Each phase requires human approval before the next begins
- **Dual model support**: Run locally (HuggingFace/torch) or via Google Gemini API
- **Assessment Pack export**: Download all approved artifacts as a single ZIP
- **Web UI + CLI**: Browser-based SPA or command-line interface

## Quick Start

### Prerequisites

- Python 3.10+
- 8GB+ RAM (for local model) or a Google Gemini API key (for hosted model)

### Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyTorch CPU-only (skip if using Gemini only)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install all dependencies
pip install -r requirements.txt -r backend/requirements.txt
```

### Start the backend

```bash
uvicorn backend.app.main:app --reload --port 8000
```

### Open the frontend

```bash
open frontend/app.html
```

Verify at:
- Backend health: http://localhost:8000/
- Swagger docs: http://localhost:8000/docs
- Frontend SPA: `frontend/app.html` in browser

## Model Configuration

The project supports two model providers. Set via environment variables or CLI flags.

### Option A: Local model (default)

Uses HuggingFace Qwen model running on your machine. No API key needed.

```bash
# Default - no extra config required
uvicorn backend.app.main:app --reload --port 8000
```

The first run will download the Qwen model (~3GB). Subsequent runs use the cached model.

### Option B: Google Gemini (hosted)

Uses Google's Gemini API. Faster, no local GPU needed, better output quality.

**1. Get an API key:**
- Go to https://aistudio.google.com/apikey
- Create an API key

**2. Create a `.env` file** in the project root (copy from the template):

```bash
cp .env.example .env
```

Then edit `.env`:

```env
PRDGEN_PROVIDER=gemini
GOOGLE_API_KEY=your-api-key-here
```

The `.env` file is gitignored so your key won't be committed.

**3. Start the backend:**

```bash
uvicorn backend.app.main:app --reload --port 8000
```

You can also set these as shell environment variables instead if you prefer — shell env vars take precedence over `.env`.

### Switching between providers

Edit `PRDGEN_PROVIDER` in your `.env` file and restart the backend:

```env
# .env — switch to Gemini
PRDGEN_PROVIDER=gemini

# .env — switch back to local
PRDGEN_PROVIDER=local
```

## Phased Generation Workflow

The v2 guided flow walks users through 6 screens:

```
Create Project -> Create Assessment -> Choose Path (Greenfield/Modernization)
     -> Questionnaire -> Upload Documents -> Phase Dashboard
```

### Phase 1: Foundation
- Context Summary, Corpus Summary, PRD, Capabilities
- Requires: questionnaire + uploaded documents

### Phase 2: Planning
- Capability Cards, Epics, Features, Roadmap
- Requires: Phase 1 approved

### Phase 3: Detail
- User Stories (Gherkin), Technical Architecture, Lean Canvas
- Requires: Phase 2 approved

Each phase produces artifacts for review. You can edit editable artifacts (e.g., PRD) before approving. Rejected phases can be regenerated with feedback.

After all 3 phases are approved, download the consolidated **Assessment Pack** ZIP.

## CLI Usage

```bash
# Local model (default)
python -m prdgen.cli \
  --input-dir examples/loan_underwriting_docs \
  --outdir out

# Gemini model
python -m prdgen.cli \
  --provider gemini \
  --input-dir examples/loan_underwriting_docs \
  --outdir out

# Single file input
python -m prdgen.cli \
  --input examples/intent_analytics.txt \
  --outdir out
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--provider` | `local` or `gemini` | `local` |
| `--gemini-model` | Gemini model name | `gemini-2.0-flash` |
| `--model-id` | HuggingFace model ID (local only) | `Qwen/Qwen2.5-1.5B-Instruct` |
| `--device` | `cpu` or `cuda` (local only) | `cpu` |
| `--max-new-tokens` | Max tokens per generation | `800` |
| `--temperature` | Generation temperature | `0.5` |
| `--input-dir` | Folder with input documents | - |
| `--input` | Single input file | - |
| `--outdir` | Output directory | `out` |

## Output Artifacts

| File | Phase | Description |
|------|-------|-------------|
| `context_summary.md` | 1 | Structured analysis of input documents |
| `corpus_summary.md` | 1 | Consolidated summary of all inputs |
| `prd.md` | 1 | Product Requirements Document |
| `capabilities.md` | 1 | Hierarchical capability map (L0/L1/L2) |
| `capability_cards.md` | 2 | Detailed L1 capability cards |
| `epics.md` | 2 | High-level epics with acceptance criteria |
| `features.md` | 2 | Epic-aware features with acceptance criteria |
| `roadmap.md` | 2 | Delivery roadmap |
| `user_stories.md` | 3 | Developer-ready stories with Gherkin criteria |
| `architecture_reference.md` | 3 | Technical architecture with Mermaid diagrams |
| `lean_canvas.md` | 3 | Business model canvas |

## API Reference

Base URL: `http://localhost:8000/api/v2`

### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions` | Create a new session |
| GET | `/sessions` | List all sessions |
| GET | `/sessions/{id}` | Get session details |

### Questionnaire
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions/{id}/questionnaire` | Get questions + saved answers |
| POST | `/sessions/{id}/questionnaire` | Submit answers |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions/{id}/upload` | Upload documents (multipart) |

### Phases
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions/{id}/phases/{n}/generate` | Start phase generation |
| GET | `/sessions/{id}/phases/{n}/status` | Get generation progress |
| GET | `/sessions/{id}/phases/{n}/review` | Get artifacts for review |
| POST | `/sessions/{id}/phases/{n}/approve` | Approve phase |
| POST | `/sessions/{id}/phases/{n}/reject` | Reject with feedback |

### Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions/{id}/export` | Download Assessment Pack ZIP |
| GET | `/sessions/{id}/snapshots/{n}/download` | Download single phase snapshot |

Full interactive docs at http://localhost:8000/docs

## Project Structure

```
PRD-Generator-MVP/
├── prdgen/                     # Core generation library
│   ├── cli.py                  # Command-line interface
│   ├── config.py               # Configuration (provider, model, params)
│   ├── model.py                # ModelProvider abstraction (Local + Gemini)
│   ├── generator.py            # Artifact generation with dependency resolution
│   ├── prompts.py              # LLM prompt templates
│   ├── ingest.py               # Document ingestion (.txt, .md, .docx)
│   ├── phased/                 # Phased generation engine
│   │   ├── phases.py           # Phase definitions, snapshots, SHA-256 hashing
│   │   └── flows.py            # PhasedFlowRunner orchestrator
│   └── intake/                 # Questionnaire system
│       └── questionnaire.py    # Question bank + validation
├── backend/                    # FastAPI web backend
│   ├── app/
│   │   ├── main.py             # FastAPI app + startup
│   │   ├── routers/v2.py       # V2 phased API endpoints
│   │   ├── services/
│   │   │   └── phase_service.py # Phase orchestration + persistence
│   │   ├── store/
│   │   │   └── phase_store.py  # SQLite persistence (WAL mode)
│   │   └── models/
│   │       └── phase_models.py # Pydantic request/response models
│   └── requirements.txt
├── frontend/                   # Web UI
│   ├── app.html                # V2 SPA (guided phased flow)
│   ├── index.html              # V1 single-shot UI (legacy)
│   └── js/
│       ├── api.js              # V2 API client
│       ├── store.js            # localStorage CRUD
│       ├── components.js       # Reusable UI builders
│       ├── app.js              # Router + screen orchestration
│       ├── questionnaire.js    # Dynamic form + auto-save
│       ├── dashboard.js        # Phase cards + progress polling
│       └── review.js           # Artifact review + editing
├── requirements.txt            # Python dependencies
└── README.md
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'torch'`
Install PyTorch CPU-only:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Gemini returns `ValueError: API key required`
Ensure the env var is set in the same shell session:
```bash
echo $GOOGLE_API_KEY   # should print your key
echo $PRDGEN_PROVIDER  # should print "gemini"
```

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use a different port
uvicorn backend.app.main:app --port 8001
```

### Frontend can't connect to backend
- Verify backend is running on http://localhost:8000
- Check browser console for CORS errors
- The frontend `api.js` expects the backend at `http://localhost:8000/api/v2`

### Slow generation (local model)
- Use `--device cuda` if you have a GPU
- Reduce `--max-new-tokens` for faster outputs
- Or switch to `PRDGEN_PROVIDER=gemini` for cloud-hosted inference

## License

MIT
