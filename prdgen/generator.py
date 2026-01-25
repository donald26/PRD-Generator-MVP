import logging
import time
from typing import Dict, Any, Tuple, List, Optional, Callable
from pathlib import Path

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
from .utils import ensure_sections, strip_trailing_noise, validate_output
from .ingest import IngestedDoc, format_corpus
from .capability_cards import extract_l1_names, ensure_cards_for_l1
from .epics import ensure_epics_for_all_l1, add_epic_summary_header, extract_epic_ids
from .features import add_feature_summary_header, ensure_features_for_epics, extract_feature_ids
from .stories import add_story_summary_header, ensure_stories_for_features
from .artifact_types import ArtifactType, ARTIFACT_FILENAMES, get_artifact_set, validate_artifact_names
from .dependencies import ArtifactDependencyResolver, ArtifactCache

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
    step_name: str = "generation",
) -> str:
    LOG.info(f"▶ Starting: {step_name}")
    LOG.debug(f"  Input prompt: {len(user_prompt)} chars, max_tokens={max_new_tokens}, temp={temperature}")

    prompt = build_chat_input(loaded.tokenizer, system, user_prompt)
    LOG.debug(f"  Full prompt: {len(prompt)} chars")

    out = generate_text(
        loaded,
        prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=cfg.top_p,
        repetition_penalty=cfg.repetition_penalty,
    )

    # Validate and clean output
    out = validate_output(out, step_name)

    LOG.info(f"✓ Completed: {step_name} ({len(out)} chars)")
    return strip_trailing_noise(out)


class ArtifactGenerator:
    """
    Modular artifact generator with dependency resolution and caching.
    Each artifact type has its own generation method.
    """

    def __init__(
        self,
        loaded: LoadedModel,
        cfg: GenerationConfig,
        docs: List[IngestedDoc],
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize artifact generator.

        Args:
            loaded: Loaded LLM model
            cfg: Generation configuration
            docs: Ingested documents
            progress_callback: Optional callback(artifact, status, progress, message)
        """
        self.loaded = loaded
        self.cfg = cfg
        self.docs = docs
        self.corpus = format_corpus(docs)
        self.progress_callback = progress_callback

        # Cache for generated artifacts (in-memory + optional disk)
        self.cache = ArtifactCache(cache_dir=cfg.cache_dir if cfg.use_cache else None)
        if cfg.use_cache:
            self.cache.load_from_disk()

        # Metadata tracking
        self.meta: Dict[str, Any] = {
            "model_id": cfg.model_id,
            "timings": {},
            "generation": as_dict(cfg),
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.meta["inputs"] = [
            {"path": d.path, "kind": d.kind, "chars": len(d.content)}
            for d in docs
        ]

    def _report_progress(self, artifact_type: ArtifactType, status: str, progress: int, message: str):
        """Report progress if callback provided"""
        if self.progress_callback:
            try:
                self.progress_callback(
                    artifact=artifact_type.value,
                    status=status,
                    progress=progress,
                    message=message
                )
            except Exception as e:
                LOG.warning(f"Progress callback error: {e}")

    def _save_artifact(self, artifact_type: ArtifactType, content: str):
        """Save artifact to disk if incremental saving enabled"""
        if not self.cfg.save_incremental or not self.cfg.output_dir:
            return

        try:
            output_path = Path(self.cfg.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            filename = ARTIFACT_FILENAMES[artifact_type]
            (output_path / filename).write_text(content, encoding='utf-8')

            LOG.info(f"Saved {artifact_type.value} ({len(content)} chars) to {filename}")
        except Exception as e:
            LOG.error(f"Failed to save {artifact_type.value}: {e}")

    def generate_corpus_summary(self) -> str:
        """Generate corpus summary (always required)"""
        artifact_type = ArtifactType.CORPUS_SUMMARY

        # Check cache first
        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating corpus summary...")

        t0 = time.time()
        summary_md = _run_step(
            self.loaded,
            SYSTEM_SUMMARY,
            corpus_summarize_prompt(self.corpus),
            self.cfg,
            max_new_tokens=min(self.cfg.max_new_tokens, 900),
            temperature=max(self.cfg.temperature - 0.1, 0.3),
            step_name="corpus_summary",
        )
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["corpus_summary_seconds"] = elapsed

        # Cache and save
        self.cache.set(artifact_type, summary_md)
        self._save_artifact(artifact_type, summary_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(summary_md)} chars in {elapsed}s")
        return summary_md

    def generate_prd(self) -> str:
        """Generate PRD (requires corpus summary)"""
        artifact_type = ArtifactType.PRD

        # Check cache
        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        # Ensure dependency
        summary_md = self.generate_corpus_summary()

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info(f"Dependencies: corpus_summary")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating PRD...")

        t0 = time.time()
        prd_md = _run_step(
            self.loaded,
            SYSTEM_PRD,
            prd_prompt(summary_md),
            self.cfg,
            max_new_tokens=self.cfg.max_new_tokens,
            temperature=self.cfg.temperature,
            step_name="prd",
        )
        prd_md = ensure_sections(prd_md, PRD_OUTLINE)
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["prd_seconds"] = elapsed

        self.cache.set(artifact_type, prd_md)
        self._save_artifact(artifact_type, prd_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(prd_md)} chars in {elapsed}s")
        return prd_md

    def generate_capabilities(self) -> str:
        """Generate Capabilities Map"""
        artifact_type = ArtifactType.CAPABILITIES

        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        # Dependencies
        prd_md = self.generate_prd()

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info(f"Dependencies: prd")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating capability map...")

        t0 = time.time()
        caps_md = _run_step(
            self.loaded,
            SYSTEM_CAPS,
            capabilities_prompt(prd_md),
            self.cfg,
            max_new_tokens=min(self.cfg.max_new_tokens, 900),
            temperature=max(self.cfg.temperature - 0.2, 0.3),
            step_name="capabilities",
        )
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["capabilities_seconds"] = elapsed

        self.cache.set(artifact_type, caps_md)
        self._save_artifact(artifact_type, caps_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(caps_md)} chars in {elapsed}s")
        return caps_md

    def generate_capability_cards(self) -> str:
        """Generate Capability Cards"""
        artifact_type = ArtifactType.CAPABILITY_CARDS

        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        # Dependencies
        prd_md = self.generate_prd()
        caps_md = self.generate_capabilities()

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info(f"Dependencies: prd, capabilities")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating capability cards...")

        t0 = time.time()
        l1_names = extract_l1_names(caps_md)
        LOG.info(f"  Found {len(l1_names)} L1 capabilities")
        cards_md = _run_step(
            self.loaded,
            SYSTEM_CAPS,
            capability_cards_prompt(prd_md, caps_md, l1_names),
            self.cfg,
            max_new_tokens=900,
            temperature=max(self.cfg.temperature - 0.2, 0.3),
            step_name="capability_cards",
        )
        cards_md = ensure_cards_for_l1(cards_md, l1_names)
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["capability_cards_seconds"] = elapsed

        self.cache.set(artifact_type, cards_md)
        self._save_artifact(artifact_type, cards_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(cards_md)} chars in {elapsed}s")
        return cards_md

    def generate_epics(self) -> str:
        """Generate Epics"""
        artifact_type = ArtifactType.EPICS

        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        # Dependencies
        prd_md = self.generate_prd()
        caps_md = self.generate_capabilities()
        cards_md = self.generate_capability_cards()

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info(f"Dependencies: prd, capabilities, capability_cards")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating epics...")

        t0 = time.time()
        l1_names = extract_l1_names(caps_md)
        LOG.info(f"  Creating epics for {len(l1_names)} L1 capabilities")
        epics_md = _run_step(
            self.loaded,
            SYSTEM_CAPS,
            epics_prompt(prd_md, caps_md, cards_md),
            self.cfg,
            max_new_tokens=1200,
            temperature=max(self.cfg.temperature - 0.2, 0.3),
            step_name="epics",
        )
        epics_md = ensure_epics_for_all_l1(epics_md, l1_names)
        epics_md = add_epic_summary_header(epics_md)
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["epics_seconds"] = elapsed

        self.cache.set(artifact_type, epics_md)
        self._save_artifact(artifact_type, epics_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(epics_md)} chars in {elapsed}s")
        return epics_md

    def generate_features(self) -> str:
        """Generate Features"""
        artifact_type = ArtifactType.FEATURES

        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        # Dependencies
        prd_md = self.generate_prd()
        epics_md = self.generate_epics()

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info(f"Dependencies: prd, epics")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating features...")

        t0 = time.time()
        epic_ids = extract_epic_ids(epics_md)
        LOG.info(f"  Creating features for {len(epic_ids)} epics")
        features_md = _run_step(
            self.loaded,
            SYSTEM_FEATURES,
            features_prompt(prd_md, epics_md),
            self.cfg,
            max_new_tokens=1400,
            temperature=max(self.cfg.temperature - 0.1, 0.2),
            step_name="features",
        )
        features_md = ensure_features_for_epics(features_md, epic_ids)
        features_md = add_feature_summary_header(features_md, epics_md)
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["features_seconds"] = elapsed

        self.cache.set(artifact_type, features_md)
        self._save_artifact(artifact_type, features_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(features_md)} chars in {elapsed}s")
        return features_md

    def generate_user_stories(self) -> str:
        """Generate User Stories"""
        artifact_type = ArtifactType.USER_STORIES

        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        # Dependencies
        prd_md = self.generate_prd()
        epics_md = self.generate_epics()
        features_md = self.generate_features()

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info(f"Dependencies: prd, epics, features")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating user stories...")

        t0 = time.time()
        feature_ids = extract_feature_ids(features_md)
        LOG.info(f"  Creating user stories for {len(feature_ids)} features")
        stories_md = _run_step(
            self.loaded,
            SYSTEM_STORIES,
            user_stories_prompt(prd_md, epics_md, features_md),
            self.cfg,
            max_new_tokens=1600,
            temperature=max(self.cfg.temperature - 0.2, 0.3),
            step_name="user_stories",
        )
        stories_md = ensure_stories_for_features(stories_md, feature_ids)
        stories_md = add_story_summary_header(stories_md)
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["user_stories_seconds"] = elapsed

        self.cache.set(artifact_type, stories_md)
        self._save_artifact(artifact_type, stories_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(stories_md)} chars in {elapsed}s")
        return stories_md

    def generate_lean_canvas(self) -> str:
        """Generate Lean Canvas"""
        artifact_type = ArtifactType.LEAN_CANVAS

        if self.cache.has(artifact_type):
            LOG.info(f"✓ Using cached {artifact_type.value}")
            self._report_progress(artifact_type, "completed", 100, "Using cached version")
            self.meta["cache_hits"] += 1
            return self.cache.get(artifact_type)

        # Dependencies
        prd_md = self.generate_prd()
        caps_md = self.generate_capabilities()

        LOG.info("=" * 70)
        LOG.info(f"GENERATING: {artifact_type.value}")
        LOG.info(f"Dependencies: prd, capabilities")
        LOG.info("=" * 70)

        self.meta["cache_misses"] += 1
        self._report_progress(artifact_type, "processing", 0, "Generating lean canvas...")

        t0 = time.time()
        canvas_md = _run_step(
            self.loaded,
            SYSTEM_CANVAS,
            lean_canvas_prompt(prd_md, caps_md),
            self.cfg,
            max_new_tokens=700,
            temperature=max(self.cfg.temperature - 0.2, 0.3),
            step_name="lean_canvas",
        )
        elapsed = round(time.time() - t0, 3)
        self.meta["timings"]["lean_canvas_seconds"] = elapsed

        self.cache.set(artifact_type, canvas_md)
        self._save_artifact(artifact_type, canvas_md)
        self._report_progress(artifact_type, "completed", 100, f"Completed in {elapsed}s")

        LOG.info(f"✓ {artifact_type.value} complete: {len(canvas_md)} chars in {elapsed}s")
        return canvas_md

    def generate_selected(self) -> Dict[ArtifactType, str]:
        """
        Generate selected artifacts (with automatic dependency resolution).

        Returns:
            Dict mapping artifact_type -> content (only explicitly selected artifacts)
        """
        # Determine which artifacts to generate
        if self.cfg.selected_artifacts:
            # Convert string names to enum
            selected = validate_artifact_names(self.cfg.selected_artifacts)
        else:
            # Use default set
            selected = get_artifact_set(self.cfg.default_set)

        # Resolve dependencies (but only return selected ones)
        to_generate = ArtifactDependencyResolver.resolve(selected)

        LOG.info(f"Selected artifacts: {[a.value for a in selected]}")
        LOG.info(f"With dependencies: {[a.value for a in to_generate]}")

        # Store in metadata
        self.meta["requested_artifacts"] = [a.value for a in selected]
        self.meta["generated_artifacts"] = [a.value for a in to_generate]

        # Map artifact types to generator methods
        generator_map = {
            ArtifactType.CORPUS_SUMMARY: self.generate_corpus_summary,
            ArtifactType.PRD: self.generate_prd,
            ArtifactType.CAPABILITIES: self.generate_capabilities,
            ArtifactType.CAPABILITY_CARDS: self.generate_capability_cards,
            ArtifactType.EPICS: self.generate_epics,
            ArtifactType.FEATURES: self.generate_features,
            ArtifactType.USER_STORIES: self.generate_user_stories,
            ArtifactType.LEAN_CANVAS: self.generate_lean_canvas,
        }

        results = {}

        for artifact_type in to_generate:
            generator_func = generator_map[artifact_type]
            content = generator_func()  # This handles caching internally

            # Only include in results if explicitly selected
            if artifact_type in selected:
                results[artifact_type] = content

        # Add cache statistics to metadata
        self.meta["artifacts"] = {
            f"{a.value}_md_chars": len(content)
            for a, content in results.items()
        }

        return results


# BACKWARD COMPATIBLE: Keep existing function signature
def generate_from_folder(
    loaded: LoadedModel,
    cfg: GenerationConfig,
    docs: List[IngestedDoc],
) -> Tuple[str, str, str, str, str, str, str, str, Dict[str, Any]]:
    """
    Original function - generates ALL artifacts.
    Maintained for backward compatibility.

    Returns:
        Tuple of (summary, prd, caps, cards, epics, features, stories, canvas, meta)
    """
    # Save original config
    original_selected = cfg.selected_artifacts
    original_default_set = cfg.default_set

    # Force complete generation
    cfg.selected_artifacts = None
    cfg.default_set = "complete"

    generator = ArtifactGenerator(loaded, cfg, docs)

    # Generate all (caching will be used if enabled)
    summary_md = generator.generate_corpus_summary()
    prd_md = generator.generate_prd()
    caps_md = generator.generate_capabilities()
    cards_md = generator.generate_capability_cards()
    epics_md = generator.generate_epics()
    features_md = generator.generate_features()
    stories_md = generator.generate_user_stories()
    canvas_md = generator.generate_lean_canvas()

    # Restore original config
    cfg.selected_artifacts = original_selected
    cfg.default_set = original_default_set

    return summary_md, prd_md, caps_md, cards_md, epics_md, features_md, stories_md, canvas_md, generator.meta


# NEW: Selective generation function
def generate_artifacts_selective(
    loaded: LoadedModel,
    cfg: GenerationConfig,
    docs: List[IngestedDoc],
    progress_callback: Optional[Callable] = None
) -> Tuple[Dict[ArtifactType, str], Dict[str, Any]]:
    """
    Generate selected artifacts based on cfg.selected_artifacts or cfg.default_set.

    Args:
        loaded: Loaded LLM model
        cfg: Generation configuration (with selected_artifacts or default_set)
        docs: Ingested documents
        progress_callback: Optional callback(artifact, status, progress, message)

    Returns:
        (artifacts_dict, metadata)
        artifacts_dict: {ArtifactType -> content} for selected artifacts only
        metadata: Generation metadata including timings, cache stats, etc.
    """
    generator = ArtifactGenerator(loaded, cfg, docs, progress_callback)
    results = generator.generate_selected()
    return results, generator.meta


def generate_prd_and_features(loaded: LoadedModel, cfg: GenerationConfig, product_intent: str):
    """Backward-compatible: single intent string -> PRD + features."""
    meta: Dict[str, Any] = {"model_id": cfg.model_id, "timings": {}, "generation": as_dict(cfg)}

    LOG.info("=" * 70)
    LOG.info("GENERATING: PRD (single-file mode)")
    LOG.info("=" * 70)

    t0 = time.time()
    prd_md = _run_step(
        loaded,
        SYSTEM_PRD,
        prd_prompt(product_intent),
        cfg,
        max_new_tokens=cfg.max_new_tokens,
        temperature=cfg.temperature,
        step_name="prd",
    )
    meta["timings"]["prd_seconds"] = round(time.time() - t0, 3)
    prd_md = ensure_sections(prd_md, PRD_OUTLINE)

    LOG.info("=" * 70)
    LOG.info("GENERATING: FEATURES (single-file mode)")
    LOG.info("=" * 70)

    t1 = time.time()
    features_md = _run_step(
        loaded,
        SYSTEM_FEATURES,
        features_prompt(prd_md, ""),  # Empty epics for backward compat
        cfg,
        max_new_tokens=min(cfg.max_new_tokens, 900),
        temperature=max(cfg.temperature - 0.1, 0.2),
        step_name="features",
    )
    meta["timings"]["features_seconds"] = round(time.time() - t1, 3)

    return prd_md, features_md, meta
