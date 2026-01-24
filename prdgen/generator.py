import logging
import time
from typing import Dict, Any, Tuple, List

from .config import GenerationConfig, as_dict
from .model import LoadedModel, build_chat_input, generate_text
from .prompts import (
    corpus_summarize_prompt,
    prd_prompt,
    features_prompt,
    capabilities_prompt,
    capability_cards_prompt,
    lean_canvas_prompt,
    epics_prompt,
    user_stories_prompt,
    PRD_OUTLINE,
)
from .utils import ensure_sections, strip_trailing_noise
from .ingest import IngestedDoc, format_corpus
from .capability_cards import extract_l1_names, ensure_cards_for_l1
from .epics import ensure_epics_for_all_l1, add_epic_summary_header, extract_epic_ids
from .features import add_feature_summary_header, ensure_features_for_epics, extract_feature_ids
from .stories import add_story_summary_header, ensure_stories_for_features

LOG = logging.getLogger("prdgen.generator")

SYSTEM_SUMMARY = "You summarize multiple product documents faithfully. Do not hallucinate missing facts."
SYSTEM_PRD = "You produce high-quality PRDs. Follow the outline and do not hallucinate missing facts."
SYSTEM_FEATURES = "You produce structured feature lists derived strictly from the PRD and epics."
SYSTEM_CAPS = "You produce capability maps derived strictly from the PRD."
SYSTEM_CANVAS = "You produce Lean Canvas derived strictly from the PRD and capability map."
SYSTEM_STORIES = "You produce detailed user stories with Gherkin acceptance criteria derived strictly from features."

def _run_step(
    loaded: LoadedModel,
    system: str,
    user_prompt: str,
    cfg: GenerationConfig,
    max_new_tokens: int,
    temperature: float,
) -> str:
    prompt = build_chat_input(loaded.tokenizer, system, user_prompt)
    out = generate_text(
        loaded,
        prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=cfg.top_p,
        repetition_penalty=cfg.repetition_penalty,
    )
    return strip_trailing_noise(out)

def generate_from_folder(
    loaded: LoadedModel,
    cfg: GenerationConfig,
    docs: List[IngestedDoc],
) -> Tuple[str, str, str, str, str, str, str, str, str, Dict[str, Any]]:
    """Folder pipeline:
    0) Corpus summary
    1) PRD
    2) Capability map (L0/L1/L2)
    2.5) L1 capability cards
    3) Epics (from capabilities)
    3.5) Features (epic-aware with acceptance criteria)
    3.75) User Stories (from features)
    4) Lean Canvas
    """
    meta: Dict[str, Any] = {"model_id": cfg.model_id, "timings": {}, "generation": as_dict(cfg)}
    meta["inputs"] = [{"path": d.path, "kind": d.kind, "chars": len(d.content)} for d in docs]

    corpus = format_corpus(docs)

    # Step 0: corpus summary
    t0 = time.time()
    summary_md = _run_step(
        loaded,
        SYSTEM_SUMMARY,
        corpus_summarize_prompt(corpus),
        cfg,
        max_new_tokens=min(cfg.max_new_tokens, 900),
        temperature=max(cfg.temperature - 0.1, 0.3),
    )
    meta["timings"]["corpus_summary_seconds"] = round(time.time() - t0, 3)

    # Step 1: PRD
    t1 = time.time()
    prd_md = _run_step(
        loaded,
        SYSTEM_PRD,
        prd_prompt(summary_md),
        cfg,
        max_new_tokens=cfg.max_new_tokens,
        temperature=cfg.temperature,
    )
    prd_md = ensure_sections(prd_md, PRD_OUTLINE)
    meta["timings"]["prd_seconds"] = round(time.time() - t1, 3)

    # Step 2: Capabilities
    t2 = time.time()
    caps_md = _run_step(
        loaded,
        SYSTEM_CAPS,
        capabilities_prompt(prd_md),
        cfg,
        max_new_tokens=min(cfg.max_new_tokens, 900),
        temperature=max(cfg.temperature - 0.2, 0.3),
    )
    meta["timings"]["capabilities_seconds"] = round(time.time() - t2, 3)

    # Step 2.5: L1 Capability Cards
    t2b = time.time()
    l1_names = extract_l1_names(caps_md)
    cards_md = _run_step(
        loaded,
        SYSTEM_CAPS,
        capability_cards_prompt(prd_md, caps_md, l1_names),
        cfg,
        max_new_tokens=900,
        temperature=max(cfg.temperature - 0.2, 0.3),
    )
    cards_md = ensure_cards_for_l1(cards_md, l1_names)
    meta["timings"]["capability_cards_seconds"] = round(time.time() - t2b, 3)

    # Step 3: Epics
    t3 = time.time()
    epics_md = _run_step(
        loaded,
        SYSTEM_CAPS,
        epics_prompt(prd_md, caps_md, cards_md),
        cfg,
        max_new_tokens=1200,
        temperature=max(cfg.temperature - 0.2, 0.3),
    )
    epics_md = ensure_epics_for_all_l1(epics_md, l1_names)
    epics_md = add_epic_summary_header(epics_md)
    meta["timings"]["epics_seconds"] = round(time.time() - t3, 3)

    # Step 3.5: Features (epic-aware)
    t3b = time.time()
    features_md = _run_step(
        loaded,
        SYSTEM_FEATURES,
        features_prompt(prd_md, epics_md),
        cfg,
        max_new_tokens=1400,
        temperature=max(cfg.temperature - 0.1, 0.2),
    )
    epic_ids = extract_epic_ids(epics_md)
    features_md = ensure_features_for_epics(features_md, epic_ids)
    features_md = add_feature_summary_header(features_md, epics_md)
    meta["timings"]["features_seconds"] = round(time.time() - t3b, 3)

    # Step 3.75: User Stories
    t3c = time.time()
    stories_md = _run_step(
        loaded,
        SYSTEM_STORIES,
        user_stories_prompt(prd_md, epics_md, features_md),
        cfg,
        max_new_tokens=1600,
        temperature=max(cfg.temperature - 0.2, 0.3),
    )
    feature_ids = extract_feature_ids(features_md)
    stories_md = ensure_stories_for_features(stories_md, feature_ids)
    stories_md = add_story_summary_header(stories_md)
    meta["timings"]["user_stories_seconds"] = round(time.time() - t3c, 3)

    # Step 4: Lean Canvas
    t4 = time.time()
    canvas_md = _run_step(
        loaded,
        SYSTEM_CANVAS,
        lean_canvas_prompt(prd_md, caps_md),
        cfg,
        max_new_tokens=700,
        temperature=max(cfg.temperature - 0.2, 0.3),
    )
    meta["timings"]["lean_canvas_seconds"] = round(time.time() - t4, 3)

    meta["artifacts"] = {
        "corpus_summary_md_chars": len(summary_md),
        "prd_md_chars": len(prd_md),
        "capabilities_md_chars": len(caps_md),
        "capability_cards_md_chars": len(cards_md),
        "epics_md_chars": len(epics_md),
        "features_md_chars": len(features_md),
        "user_stories_md_chars": len(stories_md),
        "lean_canvas_md_chars": len(canvas_md),
    }

    return summary_md, prd_md, caps_md, cards_md, epics_md, features_md, stories_md, canvas_md, meta

def generate_prd_and_features(loaded: LoadedModel, cfg: GenerationConfig, product_intent: str):
    """Backward-compatible: single intent string -> PRD + features."""
    meta: Dict[str, Any] = {"model_id": cfg.model_id, "timings": {}, "generation": as_dict(cfg)}

    t0 = time.time()
    prd_md = _run_step(
        loaded,
        SYSTEM_PRD,
        prd_prompt(product_intent),
        cfg,
        max_new_tokens=cfg.max_new_tokens,
        temperature=cfg.temperature,
    )
    meta["timings"]["prd_seconds"] = round(time.time() - t0, 3)
    prd_md = ensure_sections(prd_md, PRD_OUTLINE)

    t1 = time.time()
    features_md = _run_step(
        loaded,
        SYSTEM_FEATURES,
        features_prompt(prd_md),
        cfg,
        max_new_tokens=min(cfg.max_new_tokens, 900),
        temperature=max(cfg.temperature - 0.1, 0.2),
    )
    meta["timings"]["features_seconds"] = round(time.time() - t1, 3)

    return prd_md, features_md, meta
