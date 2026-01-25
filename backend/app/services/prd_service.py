"""
PRD Generation Service
Wraps the existing prdgen module to provide artifact generation
"""
import sys
from pathlib import Path
import json
import logging
from typing import Optional, Set, Dict

# Add parent directory to path to import prdgen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from prdgen.model import load_llama
from prdgen.generator import generate_from_folder, generate_artifacts_selective as gen_selective
from prdgen.config import GenerationConfig
from prdgen.ingest import ingest_folder
from prdgen.artifact_types import ArtifactType, ARTIFACT_FILENAMES
from prdgen.formatters import save_artifacts

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


def generate_artifacts_selective(
    input_dir: str,
    output_dir: str,
    selected_artifacts: Optional[Set[str]] = None,
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
    max_new_tokens: int = 800,
    temperature: float = 0.5,
    device: str = "cpu",
    use_cache: bool = True,
    output_formats: Set[str] = {"markdown", "json", "html"},
    progress_callback = None
) -> Dict:
    """
    Generate selected artifacts with caching and multiple output formats.

    Args:
        input_dir: Directory containing input documents
        output_dir: Directory to save generated artifacts
        selected_artifacts: Set of artifact names, or None for default ("business")
        model_id: Hugging Face model ID
        max_new_tokens: Maximum tokens for generation
        temperature: Generation temperature
        device: Device to run model on (cpu/cuda)
        use_cache: Reuse previously generated artifacts
        output_formats: Which formats to generate ("markdown", "json", "html")
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with generated artifacts and metadata
    """
    try:
        logger.info(f"Starting selective generation")
        logger.info(f"Selected artifacts: {selected_artifacts or 'default (business)'}")

        if progress_callback:
            progress_callback("Initializing", "processing", 5, "Loading model...")

        # Load model
        loaded_model = get_model(model_id, device)

        if progress_callback:
            progress_callback("Model Loaded", "completed", 15, "Model ready")

        # Create config with selection
        cfg = GenerationConfig(
            model_id=model_id,
            device=device,
            dtype="auto",
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            selected_artifacts=selected_artifacts,
            default_set="business",  # Per user preference
            save_incremental=True,
            output_dir=output_dir,
            use_cache=use_cache,
            cache_dir=Path(output_dir) if use_cache else None,
            output_formats=output_formats
        )

        if progress_callback:
            progress_callback("Ingesting Documents", "processing", 20, "Reading files...")

        # Ingest documents
        docs = ingest_folder(
            input_dir,
            include_exts=[".txt", ".md", ".docx"],
            max_files=25,
            max_chars_per_file=12000
        )

        logger.info(f"Ingested {len(docs)} documents")

        # Enhanced progress callback
        def enhanced_progress(artifact: str, status: str, progress: int, message: str):
            if progress_callback:
                # Scale progress from 20-95
                scaled_progress = 20 + int(progress * 0.75)
                progress_callback(artifact, status, scaled_progress, message)

        # Generate selected artifacts
        artifacts_dict, meta = gen_selective(
            loaded_model,
            cfg,
            docs,
            progress_callback=enhanced_progress
        )

        if progress_callback:
            progress_callback("Formatting", "processing", 95, "Generating output formats...")

        # Convert ArtifactType keys to string keys for saving
        artifacts_str_dict = {
            ARTIFACT_FILENAMES[k].replace('.md', ''): v
            for k, v in artifacts_dict.items()
        }

        # Save in requested formats
        save_artifacts(artifacts_str_dict, Path(output_dir), cfg.output_formats, meta)

        # Save metadata
        (Path(output_dir) / "run.json").write_text(json.dumps(meta, indent=2))

        if progress_callback:
            progress_callback("Complete", "completed", 100, "All artifacts generated")

        logger.info("Selective generation complete")

        return {
            "artifacts": [k.value for k in artifacts_dict.keys()],
            "metadata": meta,
            "output_dir": output_dir,
            "formats": list(output_formats)
        }

    except Exception as e:
        logger.error(f"Error in selective generation: {e}")
        if progress_callback:
            progress_callback("Error", "failed", 0, str(e))
        raise
