# Phase 1A Usage Guide

## Quick Start

The Document Context Assessment (Phase 1A) is now automatically enabled in your PRD generation pipeline.

### Basic Usage (CLI)

```bash
# Context summary is now generated first automatically
prdgen --input-dir ./my-documents --outdir ./output

# Output will include:
# - output/context_summary.md
# - output/context_summary.json
# - output/corpus_summary.md
# - output/prd.md
# ... (all other artifacts)
```

### Programmatic Usage

```python
from prdgen.config import GenerationConfig
from prdgen.model import load_llama
from prdgen.generator import ArtifactGenerator
from prdgen.ingest import ingest_folder

# 1. Configure with context summary enabled (default)
cfg = GenerationConfig(
    enable_context_summary=True,  # Default: True
    include_source_traceability=True,  # Default: True
    output_dir="./output",
    save_incremental=True,
    use_cache=True
)

# 2. Load model
loaded = load_llama(cfg.model_id, device=cfg.device)

# 3. Ingest documents
docs = ingest_folder(
    "./my-documents",
    include_exts=[".txt", ".md", ".docx"],
    max_files=25
)

# 4. Generate artifacts
generator = ArtifactGenerator(loaded, cfg, docs)
results = generator.generate_selected()  # Includes context summary automatically

# 5. Access context summary
if ArtifactType.CONTEXT_SUMMARY in results:
    context_md = results[ArtifactType.CONTEXT_SUMMARY]
    print(f"Generated context summary: {len(context_md)} chars")
```

### Selective Generation

```python
from prdgen.artifact_types import ArtifactType

# Generate ONLY context summary
cfg = GenerationConfig(
    selected_artifacts={ArtifactType.CONTEXT_SUMMARY.value}
)
results = generator.generate_selected()
# Output: context_summary.md and context_summary.json only

# Generate context summary + PRD
cfg = GenerationConfig(
    selected_artifacts={
        ArtifactType.CONTEXT_SUMMARY.value,
        ArtifactType.PRD.value
    }
)
results = generator.generate_selected()
# Output: context_summary.md/json + corpus_summary.md + prd.md
```

### Backend API Usage

```python
from backend.app.services.prd_service import generate_artifacts_selective

# API call with context summary
result = generate_artifacts_selective(
    input_dir="./uploads/user_docs",
    output_dir="./outputs/session_id",
    selected_artifacts=None,  # Uses default "business" set
    use_cache=True,
    progress_callback=my_progress_handler
)

# Context summary is generated first automatically
# Files created:
# - outputs/session_id/context_summary.md
# - outputs/session_id/context_summary.json
# - outputs/session_id/corpus_summary.md
# - outputs/session_id/prd.md
# - outputs/session_id/capabilities.md
# - outputs/session_id/lean_canvas.md
```

## Configuration Options

### Enable/Disable Context Summary

```python
# Enable (default)
cfg = GenerationConfig(enable_context_summary=True)

# Disable (backward compatible - works exactly as before)
cfg = GenerationConfig(enable_context_summary=False)
```

### Source Traceability

```python
# Include source file tracking (default)
cfg = GenerationConfig(include_source_traceability=True)

# Disable source tracking (smaller output)
cfg = GenerationConfig(include_source_traceability=False)
```

### Caching

```python
# Enable caching (recommended for iterative development)
cfg = GenerationConfig(
    use_cache=True,
    cache_dir=Path("./outputs/session_id")
)

# Disable caching (always regenerate)
cfg = GenerationConfig(use_cache=False)
```

## Output Files

### context_summary.md
Human-readable markdown with all extracted information:
- Problem/Opportunity
- Goals and Non-Goals
- Target Personas
- Key Requirements
- Constraints & Assumptions
- Risks, Gaps, Questions
- Source Traceability

### context_summary.json
Machine-readable JSON with structured data:
```json
{
  "problem_opportunity": "...",
  "goals": [...],
  "non_goals": [...],
  "target_personas": [...],
  "key_functional_requirements": [...],
  "constraints_assumptions": {
    "technical_constraints": [...],
    "business_constraints": [...],
    "assumptions": [...]
  },
  "risks_gaps_questions": {
    "risks": [...],
    "information_gaps": [...],
    "open_questions": [...],
    "conflicts": [...]
  },
  "source_traceability": {...}
}
```

## Programmatic Access

### Parse Existing Context Summary

```python
from prdgen.context_summary import parse_context_summary_markdown
from pathlib import Path

# Read and parse existing context summary
md_content = Path("output/context_summary.md").read_text()
context_dict = parse_context_summary_markdown(md_content)

# Access structured data
print(f"Problem: {context_dict['problem_opportunity']}")
print(f"Goals: {context_dict['goals']}")
print(f"Risks: {context_dict['risks_gaps_questions']['risks']}")
```

### Format for Downstream Consumption

```python
from prdgen.context_summary import format_context_summary_for_consumption

# Create consumable format for other artifacts
consumable = format_context_summary_for_consumption(context_dict)

# This can be included in prompts for downstream artifacts
# (Future enhancement - not yet implemented)
```

## Console Output

When context summary is generated, you'll see:

```
======================================================================
GENERATING: context_summary (PHASE 1A)
Processing 3 input documents
======================================================================
▶ Starting: context_summary
  Input prompt: 15234 chars, max_tokens=1200, temp=0.5
✓ Completed: context_summary (2847 chars)
Saved context summary JSON to context_summary.json
✓ context_summary complete: 2847 chars in 12.3s
```

## Error Handling

### If Generation Fails

```python
try:
    context_md = generator.generate_context_summary()
except Exception as e:
    print(f"Context summary generation failed: {e}")
    # Fallback: continue with corpus_summary
    # (Context summary failure doesn't break pipeline)
```

### If Disabled

```python
cfg = GenerationConfig(enable_context_summary=False)
generator = ArtifactGenerator(loaded, cfg, docs)

# generate_context_summary() returns empty string
context_md = generator.generate_context_summary()
# context_md == ""

# No context_summary.md or context_summary.json files created
```

## Integration with Existing Artifacts

### Current State (Phase 1A)
- Context summary is generated first
- Other artifacts (PRD, Epics, etc.) **do not yet** consume it
- Context summary is standalone and informational

### Future Enhancement (Not Implemented)
These will be added in later phases:

```python
# FUTURE: PRD could use context summary as input
# (Not implemented yet)
prd_md = _run_step(
    loaded,
    SYSTEM_PRD,
    prd_prompt(summary_md, context_summary=context_md),  # Future
    cfg,
    ...
)
```

## Best Practices

### 1. Always Enable for New Projects
```python
cfg = GenerationConfig(
    enable_context_summary=True,  # Recommended
    include_source_traceability=True
)
```

### 2. Use Caching During Development
```python
cfg = GenerationConfig(
    use_cache=True,
    cache_dir=Path(output_dir)
)
# Context summary won't regenerate if already cached
```

### 3. Review Context Summary First
Before generating full PRD:
```python
# Step 1: Generate only context summary
cfg.selected_artifacts = {ArtifactType.CONTEXT_SUMMARY.value}
results = generator.generate_selected()

# Step 2: Review context_summary.md

# Step 3: Generate full suite
cfg.selected_artifacts = None  # Use default set
results = generator.generate_selected()
```

### 4. Include in Version Control
```bash
git add output/context_summary.md
git add output/context_summary.json
git commit -m "Add context summary for project requirements"
```

## Troubleshooting

### "Context summary is empty"
- Check `enable_context_summary=True` in config
- Verify input documents are not empty
- Check logs for parsing errors

### "JSON file not generated"
- Check `output_dir` is writable
- Verify `save_incremental=True`
- Check logs for JSON conversion errors

### "Source traceability missing"
- Ensure `include_source_traceability=True`
- Model output might not include sources (check prompt)

### "Context summary too long"
- Model has 1200 token limit
- Large document sets may need summarization
- Consider filtering input documents

## Performance Tips

1. **Cache Results**: Enable `use_cache=True` for iterative work
2. **Selective Generation**: Generate context summary separately first
3. **Parallel Processing**: Context summary + other artifacts can run in parallel (future)
4. **GPU Acceleration**: Use `device="cuda"` if available

## Testing

Run the test suite to verify integration:

```bash
python3 test_context_summary_simple.py
```

Expected: All tests pass ✓

---

**Questions?** See [PHASE1A_IMPLEMENTATION.md](PHASE1A_IMPLEMENTATION.md) for technical details.
