"""
PRD Generation Service
Wraps the existing prdgen module to provide artifact generation
"""
import sys
from pathlib import Path
import json
import logging

# Add parent directory to path to import prdgen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from prdgen.model import load_llama
from prdgen.generator import generate_from_folder
from prdgen.config import GenerationConfig
from prdgen.ingest import ingest_folder

logger = logging.getLogger(__name__)

# Global model instance (loaded once and reused)
_loaded_model = None
_current_model_id = None

def get_model(model_id: str = "Qwen/Qwen2.5-1.5B-Instruct", device: str = "cpu"):
    """
    Get or load the LLM model
    Model is loaded once and cached for performance
    """
    global _loaded_model, _current_model_id

    if _loaded_model is None or _current_model_id != model_id:
        logger.info(f"Loading model: {model_id} on device: {device}")
        _loaded_model = load_llama(model_id, device=device, dtype="auto")
        _current_model_id = model_id
        logger.info(f"Model loaded successfully: {model_id}")

    return _loaded_model

def generate_artifacts(
    input_dir: str,
    output_dir: str,
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
    max_new_tokens: int = 800,
    temperature: float = 0.5,
    device: str = "cpu",
    progress_callback = None
) -> bool:
    """
    Generate all PRD artifacts from input documents

    Args:
        input_dir: Directory containing input documents
        output_dir: Directory to save generated artifacts
        model_id: Hugging Face model ID
        max_new_tokens: Maximum tokens for generation
        temperature: Generation temperature
        device: Device to run model on (cpu/cuda)

    Returns:
        bool: True if generation succeeded
    """
    try:
        logger.info(f"Starting artifact generation")
        logger.info(f"Input: {input_dir}, Output: {output_dir}")

        if progress_callback:
            progress_callback("Initializing", 5, "Loading model...")

        # Get model
        loaded_model = get_model(model_id, device)

        if progress_callback:
            progress_callback("Model Loaded", 15, "Model loaded successfully")

        # Create generation config
        cfg = GenerationConfig(
            model_id=model_id,
            device=device,
            dtype="auto",
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )

        if progress_callback:
            progress_callback("Ingesting Documents", 20, "Reading documents...")

        # Ingest documents
        logger.info(f"Ingesting documents from {input_dir}")
        docs = ingest_folder(
            input_dir,
            include_exts=[".txt", ".md", ".docx"],
            max_files=25,
            max_chars_per_file=12000
        )
        logger.info(f"Ingested {len(docs)} documents")

        if progress_callback:
            progress_callback("Generating Artifacts", 30, f"Processing {len(docs)} documents...")

        # Generate all artifacts using existing prdgen code
        logger.info("Generating artifacts...")
        summary_md, prd_md, caps_md, cards_md, epics_md, features_md, stories_md, canvas_md, meta = \
            generate_from_folder(loaded_model, cfg, docs)

        if progress_callback:
            progress_callback("Writing Files", 90, "Saving artifacts to disk...")

        # Write artifacts to output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Writing artifacts to {output_dir}")

        artifacts = {
            "corpus_summary.md": summary_md,
            "prd.md": prd_md,
            "capabilities.md": caps_md,
            "capability_cards.md": cards_md,
            "epics.md": epics_md,
            "features.md": features_md,
            "user_stories.md": stories_md,
            "lean_canvas.md": canvas_md,
            "run.json": json.dumps(meta, indent=2)
        }

        for filename, content in artifacts.items():
            file_path = output_path / filename
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"Wrote: {filename} ({len(content)} chars)")

        logger.info("All artifacts generated successfully")
        return True

    except Exception as e:
        logger.error(f"Error generating artifacts: {str(e)}")
        raise
