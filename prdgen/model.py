import logging
import re
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


def _extract_assistant_response(text: str) -> str:
    """
    Extract only the assistant's response, removing any chat template artifacts.

    This handles cases where the model output includes role markers or markdown code blocks.
    """
    # Remove common chat template markers at the start
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

    # If text contains markdown code blocks, extract the content
    if cleaned.strip().startswith("```markdown\n"):
        cleaned = re.sub(r"^```markdown\n", "", cleaned.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)
    elif cleaned.strip().startswith("```\n"):
        cleaned = re.sub(r"^```\n", "", cleaned.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)

    return cleaned.strip()

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

    # Decode only the NEW tokens (not the prompt)
    prompt_length = inputs['input_ids'].shape[1]
    new_tokens = out[0][prompt_length:]
    decoded = tok.decode(new_tokens, skip_special_tokens=True)

    # Clean up any remaining chat template artifacts
    decoded = _extract_assistant_response(decoded)

    LOG.debug(f"Generated {len(decoded)} characters")
    return decoded.strip()
