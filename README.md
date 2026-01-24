# PRD Generator (Hugging Face (Qwen default)) — Product Intent → PRD + Feature List

This project turns a **high-level product intent** into:
1) a detailed **PRD** (`prd.md`)
2) a structured **Feature List** (`features.md`)

It uses **Hugging Face + instruct Instruct models** and is model-configurable.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate  # Windows PowerShell

pip install -r requirements.txt
```

> For gated LLaMA models, login first:
```bash
huggingface-cli login
```

Run:
```bash
python -m prdgen.cli   --input examples/intent_analytics.txt   --outdir out   --model-id Qwen/Qwen2.5-1.5B-Instruct
```

Outputs:
- `out/prd.md`
- `out/features.md`
- `out/run.json` (debug metadata)

Model parameters:
```bash
python -m prdgen.cli --input examples/intent_devtool.txt --outdir out   --model-id Qwen/Qwen2.5-1.5B-Instruct   --max-new-tokens 1400 --temperature 0.6 --device cpu
```

Notes:
- CPU works but is slow; use `--device cuda` if you have a GPU.
- Output quality depends on model size and compute.


## Folder mode (multiple documents)

Put meeting notes and docs in a folder (supported: .txt/.md/.log/.docx).

```bash
python -m prdgen.cli \
  --input-dir path/to/docs_folder \
  --outdir out \
  --model-id Qwen/Qwen2.5-1.5B-Instruct \
  --max-new-tokens 800 --temperature 0.5
```

Outputs:
- `out/corpus_summary.md` - Consolidated summary of all input documents
- `out/prd.md` - Product Requirements Document
- `out/capabilities.md` - Hierarchical capability map (L0/L1/L2)
- `out/capability_cards.md` - Detailed L1 capability cards with success signals
- `out/epics.md` - High-level epics from L1 capabilities
- `out/features.md` - Epic-aware features with acceptance criteria
- `out/user_stories.md` - Detailed user stories with Gherkin acceptance criteria
- `out/lean_canvas.md` - Business model canvas
- `out/run.json` - Metadata and timing information

## Pipeline Structure

The tool follows a structured top-down decomposition:

```
Documents → PRD → Capabilities (L0/L1/L2) → Epics → Features → User Stories
```

**Capability Cards** include a Success Signals section that maps to epic acceptance criteria.

**Epics** include:
- Epic ID, priority, and complexity
- Business objectives and success criteria
- Target personas and scope
- Dependencies and acceptance criteria

**Features** (epic-aware with acceptance criteria):
- Feature ID linked to parent epic
- Testable acceptance criteria (3-6 per feature)
- Priority, complexity, dependencies, and risks
- Organized by epic for traceability

**User Stories** (detailed, developer-ready):
- Story ID linked to feature and epic
- Standard "As a... I want... So that..." format
- Gherkin-style acceptance criteria (Given/When/Then)
- Story point estimates (Fibonacci scale)
- Technical notes for developers
- Definition of done checklist

## Example: Loan Underwriting (agentic AI, human-in-the-loop)

A realistic multi-document input bundle is included at:
- `examples/loan_underwriting_docs/`

Run:
```bash
python -m prdgen.cli --input-dir examples/loan_underwriting_docs --outdir out --max-new-tokens 800 --temperature 0.5
```
