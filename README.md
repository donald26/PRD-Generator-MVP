# PRD Generator

Transform high-level product intent into comprehensive PRD artifacts using local LLMs (Hugging Face models).

## Features

- **Multi-format input**: Supports `.txt`, `.md`, `.log`, `.docx` files
- **Intelligent two-step workflow**: Analyzes documents first, then recommends which artifacts to generate
- **Comprehensive output**: PRD, Capabilities, Epics, Features, User Stories, Lean Canvas
- **CLI and Web Interface**: Use via command line or browser-based UI
- **Local LLM**: Runs entirely on your machine using Hugging Face models (Qwen default)
- **Configurable**: Choose model, temperature, tokens, and which artifacts to generate

## Quick Start

### Prerequisites

- Python 3.10+
- 8GB+ RAM (16GB recommended for larger models)
- For gated LLaMA models: `huggingface-cli login`

### Installation

```bash
# Clone the repository
cd PRD-Generator-MVP

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell

# Install all dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Verify installation
python3 -c "import fastapi; import torch; print('All dependencies installed!')"
```

## Usage

### Option 1: Command Line Interface

**Single file input:**
```bash
python -m prdgen.cli \
  --input examples/intent_analytics.txt \
  --outdir out \
  --model-id Qwen/Qwen2.5-1.5B-Instruct
```

**Folder input (multiple documents):**
```bash
python -m prdgen.cli \
  --input-dir examples/loan_underwriting_docs \
  --outdir out \
  --model-id Qwen/Qwen2.5-1.5B-Instruct \
  --max-new-tokens 800 \
  --temperature 0.5
```

**CLI Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Single input file | - |
| `--input-dir` | Folder with multiple documents | - |
| `--outdir` | Output directory | `out` |
| `--model-id` | Hugging Face model ID | `Qwen/Qwen2.5-1.5B-Instruct` |
| `--max-new-tokens` | Max tokens per generation | `1200` |
| `--temperature` | Generation temperature | `0.5` |
| `--device` | `cpu` or `cuda` | `cpu` |

### Option 2: Web Application

**Start the backend server:**
```bash
cd backend
./run.sh

# Or manually:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Open the frontend:**
```bash
open frontend/index.html
# Or serve via Python:
cd frontend && python3 -m http.server 3000
```

**Web UI Features:**
- **Upload Documents**: Drag and drop files, click "Generate PRD Artifacts", download ZIP
- **Use Folder Path**: Enter path like `examples/loan_underwriting_docs`, artifacts saved to `backend/outputs/`

## Output Artifacts

The generator produces these files in the output directory:

| File | Description |
|------|-------------|
| `context_summary.md` | Structured analysis of input documents |
| `recommendation.json` | Intelligent artifact recommendations |
| `corpus_summary.md` | Consolidated summary of all inputs |
| `prd.md` | Product Requirements Document |
| `capabilities.md` | Hierarchical capability map (L0/L1/L2) |
| `capability_cards.md` | Detailed L1 capability cards |
| `epics.md` | High-level epics with acceptance criteria |
| `features.md` | Epic-aware features with acceptance criteria |
| `user_stories.md` | Developer-ready stories with Gherkin criteria |
| `lean_canvas.md` | Business model canvas |
| `run.json` | Generation metadata and timing |

## Two-Step Intelligent Workflow

The generator uses an intelligent workflow:

### Step 1: Context Assessment
Analyzes input documents to extract:
- Problem/Opportunity
- Goals and Non-Goals
- Target Personas
- Key Functional Requirements
- Constraints & Assumptions
- Risks, Gaps, and Open Questions

### Step 2: Artifact Recommendation
Based on the context analysis, recommends which artifacts to generate:

| Artifact | Recommended When |
|----------|-----------------|
| PRD | Almost always (foundation document) |
| Capabilities | 5+ functional requirements |
| Capability Cards | 8+ requirements (complex projects) |
| Epics | 3+ goals OR 5+ requirements |
| Features | 3+ requirements + personas defined |
| User Stories | 5+ requirements + personas + technical detail |
| Lean Canvas | Business-focused with clear problem statement |

Each recommendation includes a confidence score (0-100) and rationale.

## Pipeline Structure

```
Documents → Context Summary → PRD → Capabilities → Epics → Features → User Stories
                                                         └→ Lean Canvas
```

## API Reference

Base URL: `http://localhost:8000`

### POST /api/generate
Upload files and generate artifacts.

**Request:** `multipart/form-data` with files

**Response:**
```json
{
  "job_id": "uuid",
  "download_url": "/api/download/uuid",
  "status": "completed"
}
```

### POST /api/generate-from-path
Generate from existing folder.

**Request:**
```json
{"folder_path": "/path/to/documents"}
```

**Response:**
```json
{
  "job_id": "uuid",
  "output_path": "/path/to/outputs/uuid",
  "status": "completed"
}
```

### GET /api/download/{job_id}
Download generated artifacts as ZIP.

### GET /docs
Interactive API documentation (Swagger UI).

## Project Structure

```
PRD-Generator-MVP/
├── prdgen/                 # Core generation library
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Configuration classes
│   ├── generator.py       # Artifact generation logic
│   ├── model.py           # Model loading
│   ├── prompts.py         # LLM prompts
│   ├── ingest.py          # Document ingestion
│   └── recommendation.py  # Artifact recommendation logic
├── backend/               # FastAPI web backend
│   ├── app/
│   │   ├── main.py        # FastAPI app
│   │   └── services/
│   │       └── prd_service.py
│   ├── temp/              # Uploaded files (temporary)
│   ├── outputs/           # Generated artifacts
│   └── run.sh             # Startup script
├── frontend/
│   └── index.html         # Web interface
├── templates/             # Output templates
├── examples/              # Example input documents
│   └── loan_underwriting_docs/
└── requirements.txt       # Python dependencies
```

## Configuration (Programmatic)

```python
from prdgen.config import GenerationConfig
from prdgen.model import load_llama
from prdgen.generator import generate_artifacts_selective

# Load model
model = load_llama("Qwen/Qwen2.5-1.5B-Instruct")

# Configure generation
cfg = GenerationConfig(
    enable_context_summary=True,    # Enable intelligent context analysis
    enable_recommendation=True,      # Use smart artifact recommendations
    output_dir="./output",
    save_incremental=True,
    use_cache=True
)

# Generate artifacts
artifacts, metadata = generate_artifacts_selective(model, cfg, docs)
```

**Configuration Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `enable_context_summary` | Generate context assessment first | `True` |
| `enable_recommendation` | Use intelligent recommendations | `True` |
| `generate_only` | Override: generate only these artifacts | `None` |
| `default_set` | Fallback artifact set (`minimal`, `business`, `development`, `complete`) | `business` |
| `use_cache` | Cache intermediate results | `True` |

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use a different port
uvicorn app.main:app --port 8001
```

### Import errors
```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Frontend can't connect to backend
- Verify backend is running on http://localhost:8000
- Check browser console for CORS errors
- Ensure `API_URL` in `frontend/index.html` matches backend URL

### Slow generation
- Use `--device cuda` if you have a GPU
- Reduce `--max-new-tokens` for faster (but shorter) outputs
- Use smaller models for quick iterations

### Out of memory
- Use smaller models (e.g., `Qwen/Qwen2.5-1.5B-Instruct`)
- Reduce `--max-new-tokens`
- Close other applications to free RAM

## Example: Loan Underwriting

A realistic multi-document input bundle is included:

```bash
# CLI
python -m prdgen.cli \
  --input-dir examples/loan_underwriting_docs \
  --outdir out \
  --max-new-tokens 800

# Web UI: Enter "examples/loan_underwriting_docs" in folder path
```

## License

MIT
