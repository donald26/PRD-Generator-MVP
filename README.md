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
- `out/corpus_summary.md`
- `out/prd.md`
- `out/capabilities.md` (L0/L1/L2)
- `out/features.md`
- `out/lean_canvas.md`
- `out/run.json`


Folder outputs now include `out/capability_cards.md` (L1 capability cards: description, objective, personas, design considerations, related L2).


Capability cards include a **Success Signals** section per L1, which can later map to epic acceptance criteria.

## Example: Loan Underwriting (agentic AI, human-in-the-loop)

A realistic multi-document input bundle is included at:
- `examples/loan_underwriting_docs/`

Run:
```bash
python -m prdgen.cli --input-dir examples/loan_underwriting_docs --outdir out --max-new-tokens 800 --temperature 0.5
```
