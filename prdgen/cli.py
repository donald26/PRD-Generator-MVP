import argparse
import json
import logging
from pathlib import Path

from .config import GenerationConfig
from .model import load_llama
from .generator import generate_prd_and_features, generate_from_folder
from .utils import read_text, write_text
from .ingest import ingest_folder

LOG = logging.getLogger("prdgen.cli")

def main():
    ap = argparse.ArgumentParser(
        prog="prdgen",
        description="Docs/Notes Folder → PRD + Capabilities + Capability Cards + Lean Canvas (HF instruct model)",
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Path to a text file containing product intent (single-file mode)")
    src.add_argument("--input-dir", help="Path to a folder containing multiple documents (folder mode)")

    ap.add_argument("--outdir", default="out", help="Output directory")
    ap.add_argument("--model-id", default="Qwen/Qwen2.5-1.5B-Instruct", help="HF model id (default: Qwen 1.5B Instruct)")
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu", help="Device (cuda requires NVIDIA GPU)")
    ap.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto", help="Torch dtype")

    ap.add_argument("--max-new-tokens", type=int, default=800, help="Upper bound for PRD generation (demo-safe default)")
    ap.add_argument("--temperature", type=float, default=0.5)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--repetition-penalty", type=float, default=1.05)

    # Folder ingestion controls
    ap.add_argument("--max-files", type=int, default=25)
    ap.add_argument("--max-chars-per-file", type=int, default=12000)
    ap.add_argument("--include-exts", nargs="*", default=None, help="Optional list of extensions to include (e.g., .txt .md .docx)")

    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = GenerationConfig(
        model_id=args.model_id,
        device=args.device,
        dtype=args.dtype,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        repetition_penalty=args.repetition_penalty,
    )

    LOG.info("Loading model (first time may download weights)...")
    loaded = load_llama(cfg.model_id, device=cfg.device, dtype=cfg.dtype)

    if args.input_dir:
        LOG.info("Ingesting folder: %s", args.input_dir)
        docs = ingest_folder(
            args.input_dir,
            include_exts=args.include_exts,
            max_files=args.max_files,
            max_chars_per_file=args.max_chars_per_file,
        )

        LOG.info("Generating corpus summary + PRD + capabilities + capability cards + features + lean canvas...")
        summary_md, prd_md, caps_md, cards_md, features_md, canvas_md, meta = generate_from_folder(loaded, cfg, docs)

        write_text(str(outdir / "corpus_summary.md"), summary_md)
        write_text(str(outdir / "prd.md"), prd_md)
        write_text(str(outdir / "capabilities.md"), caps_md)
        write_text(str(outdir / "capability_cards.md"), cards_md)
        write_text(str(outdir / "features.md"), features_md)
        write_text(str(outdir / "lean_canvas.md"), canvas_md)
        write_text(str(outdir / "run.json"), json.dumps(meta, indent=2))

        print("✅ Wrote:")
        print(f"- {outdir/'corpus_summary.md'}")
        print(f"- {outdir/'prd.md'}")
        print(f"- {outdir/'capabilities.md'}")
        print(f"- {outdir/'capability_cards.md'}")
        print(f"- {outdir/'features.md'}")
        print(f"- {outdir/'lean_canvas.md'}")
        print(f"- {outdir/'run.json'}")
        return

    # Single intent mode (backward compatible)
    intent = read_text(args.input).strip()
    if not intent:
        raise SystemExit("Input intent file is empty")

    LOG.info("Generating PRD + features (single-file mode)...")
    prd_md, features_md, meta = generate_prd_and_features(loaded, cfg, intent)
    write_text(str(outdir / "prd.md"), prd_md)
    write_text(str(outdir / "features.md"), features_md)
    write_text(str(outdir / "run.json"), json.dumps(meta, indent=2))

    print(f"✅ Wrote:\n- {outdir/'prd.md'}\n- {outdir/'features.md'}\n- {outdir/'run.json'}")

if __name__ == "__main__":
    main()
