from dataclasses import dataclass, field
from typing import Dict, Any, Set, Optional
from pathlib import Path


@dataclass
class GenerationConfig:
    # Provider selection: "local" (HF/torch) or "gemini" (Google hosted)
    provider: str = "local"  # env override: PRDGEN_PROVIDER

    # Local model configuration (used when provider="local")
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"
    device: str = "cpu"  # "cpu" or "cuda"
    dtype: str = "auto"  # "auto", "float16", "bfloat16", "float32"

    # Gemini configuration (used when provider="gemini")
    gemini_model: str = "gemini-2.0-flash"
    gemini_api_key: Optional[str] = None  # env override: GOOGLE_API_KEY

    # Generation parameters (shared across providers)
    max_new_tokens: int = 1400
    temperature: float = 0.6
    top_p: float = 0.9
    repetition_penalty: float = 1.05  # local-only; ignored by Gemini
    prd_min_sections: int = 10
    write_debug: bool = True

    # NEW: Artifact selection
    selected_artifacts: Optional[Set[str]] = None  # None = use default_set or recommendation
    default_set: str = "business"  # "business", "minimal", "development", "complete"

    # NEW: Artifact recommendation (Phase 2)
    enable_recommendation: bool = True  # Use intelligent recommendation based on context analysis
    generate_only: Optional[Set[str]] = None  # User override: explicit list of artifacts to generate (bypasses recommendation)

    # NEW: Incremental saving
    save_incremental: bool = True  # Save each artifact as it completes
    output_dir: Optional[Path] = None  # Required if save_incremental=True

    # NEW: Caching/resume support
    use_cache: bool = True  # Reuse previously generated artifacts
    cache_dir: Optional[Path] = None  # Where to load cached artifacts from

    # NEW: Output formats
    output_formats: Set[str] = field(default_factory=lambda: {"markdown", "json", "html"})

    # NEW: Context Summary (Phase 1A)
    enable_context_summary: bool = True  # Generate structured document context assessment first
    include_source_traceability: bool = True  # Include file-level source mapping

    # NEW: Architecture Diagram
    enable_architecture_diagram: bool = True  # Generate technical architecture reference diagram
    enable_architecture_options: bool = True  # Generate alternative architecture patterns per capability

    # NEW: Template Management
    template_dir: Optional[Path] = None  # Custom template directory (None = use default templates/)

    # Phased generation (opt-in, default=False preserves existing behavior)
    phase_mode: bool = False
    flow_type: str = "greenfield"               # "greenfield" | "modernization"
    questionnaire_answers: Optional[Dict[str, str]] = None
    current_phase: Optional[int] = None          # 1, 2, or 3
    prior_snapshot_dir: Optional[Path] = None    # where to load approved snapshots

def as_dict(cfg: GenerationConfig) -> Dict[str, Any]:
    return {
        "model_id": cfg.model_id,
        "device": cfg.device,
        "dtype": cfg.dtype,
        "max_new_tokens": cfg.max_new_tokens,
        "temperature": cfg.temperature,
        "top_p": cfg.top_p,
        "repetition_penalty": cfg.repetition_penalty,
        "prd_min_sections": cfg.prd_min_sections,
        "write_debug": cfg.write_debug,
    }
