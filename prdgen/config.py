from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class GenerationConfig:
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"
    device: str = "cpu"  # "cpu" or "cuda"
    dtype: str = "auto"  # "auto", "float16", "bfloat16", "float32"
    max_new_tokens: int = 1400
    temperature: float = 0.6
    top_p: float = 0.9
    repetition_penalty: float = 1.05
    prd_min_sections: int = 10
    write_debug: bool = True

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
