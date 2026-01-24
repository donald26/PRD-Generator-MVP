import logging
from dataclasses import dataclass
from typing import Any, Dict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

LOG = logging.getLogger("prdgen.model")

DTYPE_MAP = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
    "auto": None,
}

@dataclass
class LoadedModel:
    tokenizer: Any
    model: Any
    device: str
    model_id: str

def load_llama(model_id: str, device: str = "cpu", dtype: str = "auto") -> LoadedModel:
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

def build_chat_input(tokenizer, system: str, user: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"SYSTEM: {system}\n\nUSER: {user}\n\nASSISTANT:"

@torch.inference_mode()
def generate_text(
    loaded: LoadedModel,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
) -> str:
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
    decoded = tok.decode(out[0], skip_special_tokens=True)
    # Remove prompt echo if present
    if decoded.startswith(prompt[:80]):
        decoded = decoded[len(prompt):]
    return decoded.strip()
