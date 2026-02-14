import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

LOG = logging.getLogger("prdgen.model")


# ── Provider interface ──────────────────────────────────────────────────

class ModelProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(
        self,
        system: str,
        user_prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float = 0.9,
        repetition_penalty: float = 1.05,
    ) -> str:
        """Generate text given a system prompt and user prompt. Returns the assistant response."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the model identifier string."""
        ...


# ── Local provider (HuggingFace / torch) ────────────────────────────────

@dataclass
class LoadedModel:
    tokenizer: Any
    model: Any
    device: str
    model_id: str


class LocalProvider(ModelProvider):
    """Local HuggingFace model via torch inference."""

    def __init__(self, loaded: LoadedModel):
        self._loaded = loaded

    @property
    def model_id(self) -> str:
        return self._loaded.model_id

    def generate(
        self,
        system: str,
        user_prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float = 0.9,
        repetition_penalty: float = 1.05,
    ) -> str:
        prompt = build_chat_input(self._loaded.tokenizer, system, user_prompt)
        return generate_text(
            self._loaded,
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
        )


# ── Gemini provider (Google hosted) ─────────────────────────────────────

class GeminiProvider(ModelProvider):
    """Google Gemini hosted model via google-genai SDK."""

    def __init__(self, gemini_model: str, api_key: str):
        from google import genai
        self._model_name = gemini_model
        self._client = genai.Client(api_key=api_key)
        LOG.info("GeminiProvider initialized: model=%s", gemini_model)

    @property
    def model_id(self) -> str:
        return self._model_name

    def generate(
        self,
        system: str,
        user_prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float = 0.9,
        repetition_penalty: float = 1.05,
    ) -> str:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_new_tokens,
            ),
        )

        text = response.text or ""
        text = _extract_assistant_response(text)
        LOG.debug("Gemini generated %d characters", len(text))
        return text.strip()


# ── Factory ──────────────────────────────────────────────────────────────

def load_provider(cfg) -> ModelProvider:
    """
    Create the appropriate ModelProvider based on config + env vars.

    Env var overrides:
        PRDGEN_PROVIDER  -> "local" or "gemini"
        GOOGLE_API_KEY   -> Gemini API key
    """
    provider = os.environ.get("PRDGEN_PROVIDER", cfg.provider).lower()

    if provider == "gemini":
        api_key = cfg.gemini_api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError(
                "Gemini provider requires an API key. "
                "Set GOOGLE_API_KEY env var or pass gemini_api_key in config."
            )
        return GeminiProvider(cfg.gemini_model, api_key)

    # Default: local HuggingFace model
    loaded = load_llama(cfg.model_id, device=cfg.device, dtype=cfg.dtype)
    return LocalProvider(loaded)


# ── Local model loading (existing code) ──────────────────────────────────

def load_llama(model_id: str, device: str = "cpu", dtype: str = "auto") -> LoadedModel:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    DTYPE_MAP = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
        "auto": None,
    }

    LOG.info("Loading model: %s", model_id)
    tok = AutoTokenizer.from_pretrained(model_id, use_fast=True)

    torch_dtype = DTYPE_MAP.get(dtype, None)
    kwargs: Dict[str, Any] = {}
    if torch_dtype is not None:
        kwargs["torch_dtype"] = torch_dtype
    if device == "cuda":
        kwargs["device_map"] = "auto"

    mdl = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    if device == "cpu":
        mdl = mdl.to("cpu")
    mdl.eval()
    return LoadedModel(tokenizer=tok, model=mdl, device=device, model_id=model_id)


# ── Chat prompt construction (used by LocalProvider) ─────────────────────

def build_chat_input(tokenizer, system: str, user: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"SYSTEM: {system}\n\nUSER: {user}\n\nASSISTANT:"


# ── Response cleaning (shared) ───────────────────────────────────────────

def _extract_assistant_response(text: str) -> str:
    """
    Extract only the assistant's response, removing any chat template artifacts.
    """
    patterns_to_remove = [
        r"^system\s*\n",
        r"^user\s*\n",
        r"^assistant\s*\n",
        r"^SYSTEM:.*?(?=\n\n)",
        r"^USER:.*?(?=\n\n)",
        r"^ASSISTANT:\s*",
    ]

    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE | re.DOTALL)

    if cleaned.strip().startswith("```markdown\n"):
        cleaned = re.sub(r"^```markdown\n", "", cleaned.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)
    elif cleaned.strip().startswith("```\n"):
        cleaned = re.sub(r"^```\n", "", cleaned.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)

    return cleaned.strip()


# ── Local text generation (used by LocalProvider) ────────────────────────

def generate_text(
    loaded: LoadedModel,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
) -> str:
    import torch

    with torch.inference_mode():
        tok = loaded.tokenizer
        mdl = loaded.model
        inputs = tok(prompt, return_tensors="pt")
        inputs = {k: v.to(mdl.device) for k, v in inputs.items()}

        do_sample = temperature is not None and temperature > 0.0
        out = mdl.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature if do_sample else None,
            top_p=top_p if do_sample else None,
            repetition_penalty=repetition_penalty,
            pad_token_id=tok.eos_token_id,
        )

        prompt_length = inputs['input_ids'].shape[1]
        new_tokens = out[0][prompt_length:]
        decoded = tok.decode(new_tokens, skip_special_tokens=True)

        decoded = _extract_assistant_response(decoded)

        LOG.debug(f"Generated {len(decoded)} characters")
        return decoded.strip()
