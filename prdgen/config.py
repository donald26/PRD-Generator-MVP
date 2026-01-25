from dataclasses import dataclass, field
from typing import Dict, Any, Set, Optional
from pathlib import Path

@dataclass
class GenerationConfig:
    # Existing model configuration
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"
    device: str = "cpu"  # "cpu" or "cuda"
    dtype: str = "auto"  # "auto", "float16", "bfloat16", "float32"
    max_new_tokens: int = 1400
    temperature: float = 0.6
    top_p: float = 0.9
    repetition_penalty: float = 1.05
    prd_min_sections: int = 10
    write_debug: bool = True

    # NEW: Artifact selection
    selected_artifacts: Optional[Set[str]] = None  # None = use default_set
    default_set: str = "business"  # "business", "minimal", "development", "complete"

    # NEW: Incremental saving
    save_incremental: bool = True  # Save each artifact as it completes
    output_dir: Optional[Path] = None  # Required if save_incremental=True

    # NEW: Caching/resume support
    use_cache: bool = True  # Reuse previously generated artifacts
    cache_dir: Optional[Path] = None  # Where to load cached artifacts from

    # NEW: Output formats
    output_formats: Set[str] = field(default_factory=lambda: {"markdown", "json", "html"})

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
