"""
Flow Orchestrator - Two-path phased generation with HITL gates.

Orchestrates the questionnaire -> phase gate -> generator pipeline,
managing cache seeding from approved snapshots and HITL edit propagation.
"""
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Set

from ..artifact_types import ArtifactType
from ..config import GenerationConfig
from ..dependencies import ArtifactCache
from ..generator import ArtifactGenerator
from ..ingest import IngestedDoc
from ..model import LoadedModel
from ..intake.questionnaire import (
    load_questionnaire,
    format_answers_as_context,
    format_answers_as_transcript,
    validate_answers,
    get_questionnaire_version,
)
from .phases import (
    PhaseStatus,
    PhaseSnapshot,
    PHASE_DEFINITIONS,
    get_phase_definition,
    create_snapshot,
    verify_snapshot,
    save_snapshot_to_disk,
    get_prior_snapshots,
)

LOG = logging.getLogger("prdgen.phased.flows")


class FlowType(str, Enum):
    GREENFIELD = "greenfield"
    MODERNIZATION = "modernization"


class PhasedFlowRunner:
    """
    Orchestrates phased generation with HITL gates.

    Usage:
        runner = PhasedFlowRunner(flow_type, questionnaire_answers, cfg, loaded, docs)

        # Phase 1 -- generates, returns artifacts for review
        phase1_artifacts = runner.run_phase(1)
        # ... user reviews, possibly edits maturity ratings ...
        runner.approve_phase(1, approved_by="user@co.com", notes="...")

        # Phase 2
        phase2_artifacts = runner.run_phase(2)
        runner.approve_phase(2, ...)

        # Phase 3
        phase3_artifacts = runner.run_phase(3)
        runner.approve_phase(3, ...)

        final = runner.get_all_approved_artifacts()
    """

    def __init__(
        self,
        flow_type: str,
        questionnaire_answers: Dict[str, str],
        cfg: GenerationConfig,
        loaded: LoadedModel,
        docs: List[IngestedDoc],
        snapshot_base_dir: Optional[Path] = None,
        progress_callback: Optional[Callable] = None,
    ):
        self.flow_type = FlowType(flow_type)
        self.answers = questionnaire_answers
        self.cfg = cfg
        self.loaded = loaded
        self.progress_callback = progress_callback
        self.snapshot_base_dir = snapshot_base_dir or Path("snapshots")

        # Store flow_type and answers on cfg so generator methods can access them
        self.cfg.flow_type = flow_type
        self.cfg.questionnaire_answers = questionnaire_answers
        self.cfg.phase_mode = True

        # Load questionnaire JSON
        self.questionnaire_data = load_questionnaire(flow_type)
        self.questionnaire_version = get_questionnaire_version(flow_type)

        # Produce BOTH outputs from answers
        self.structured_context = format_answers_as_context(flow_type, questionnaire_answers)
        self.raw_transcript = format_answers_as_transcript(flow_type, questionnaire_answers)

        # Create a synthetic IngestedDoc from structured context and prepend to docs
        intake_doc = IngestedDoc(
            path=f"questionnaire_{flow_type}_intake.md",
            kind="md",
            content=self.structured_context,
        )
        self.docs = [intake_doc] + list(docs)

        # Phase state tracking
        self.snapshots: Dict[int, PhaseSnapshot] = {}
        self.phase_statuses: Dict[int, PhaseStatus] = {
            1: PhaseStatus.PENDING,
            2: PhaseStatus.PENDING,
            3: PhaseStatus.PENDING,
        }
        self.phase_artifacts: Dict[int, Dict[ArtifactType, str]] = {}
        self.phase_feedback: Dict[int, str] = {}

        # The generator instance (created fresh per phase to get clean cache seeding)
        self._generator: Optional[ArtifactGenerator] = None

        LOG.info(
            f"PhasedFlowRunner initialized: flow_type={flow_type}, "
            f"questionnaire_ver={self.questionnaire_version}, "
            f"docs={len(self.docs)} (including intake)"
        )

    def run_phase(self, phase_number: int) -> Dict[ArtifactType, str]:
        """
        Generate artifacts for the given phase.

        Prerequisites:
        - If phase > 1, the prior phase must be approved.

        Returns:
            Dict of ArtifactType -> generated content for this phase's artifacts.
        """
        phase_def = get_phase_definition(phase_number)

        # Validate prerequisites
        if phase_def.requires_phase is not None:
            req = phase_def.requires_phase
            if self.phase_statuses.get(req) != PhaseStatus.APPROVED:
                raise ValueError(
                    f"Phase {phase_number} requires Phase {req} to be approved first. "
                    f"Current status: {self.phase_statuses.get(req, 'unknown')}"
                )

        LOG.info("=" * 70)
        LOG.info(f"PHASE {phase_number}: {phase_def.label}")
        LOG.info(f"Artifacts: {[a.value for a in phase_def.artifacts]}")
        LOG.info("=" * 70)

        self.phase_statuses[phase_number] = PhaseStatus.GENERATING

        # Create a fresh generator instance
        generator = ArtifactGenerator(
            self.loaded, self.cfg, self.docs, self.progress_callback
        )

        # Seed cache with all prior snapshot artifacts
        if phase_number > 1:
            prior_artifacts = get_prior_snapshots(phase_number, self.snapshots)
            for name, content in prior_artifacts.items():
                try:
                    artifact_type = ArtifactType(name)
                    generator.cache.set(artifact_type, content)
                    LOG.debug(f"  Cache seeded: {name} ({len(content)} chars)")
                except ValueError:
                    LOG.warning(f"  Unknown artifact in snapshot: {name}")

        # Configure to generate only this phase's artifacts
        self.cfg.generate_only = {a.value for a in phase_def.artifacts}
        self.cfg.current_phase = phase_number

        # Generate
        results = generator.generate_selected()

        # Store results
        self.phase_artifacts[phase_number] = results
        self.phase_statuses[phase_number] = PhaseStatus.REVIEW
        self._generator = generator

        LOG.info(
            f"Phase {phase_number} generation complete: "
            f"{len(results)} artifacts ready for review"
        )

        return results

    def approve_phase(
        self,
        phase_number: int,
        approved_by: str,
        notes: str = "",
        edited_artifacts: Optional[Dict[str, str]] = None,
    ) -> PhaseSnapshot:
        """
        Approve a phase, optionally with HITL-edited artifacts.

        If edited_artifacts is provided, the edited content replaces the
        LLM-generated version in the cache and snapshot.
        """
        if self.phase_statuses.get(phase_number) != PhaseStatus.REVIEW:
            raise ValueError(
                f"Phase {phase_number} is not in review state. "
                f"Current: {self.phase_statuses.get(phase_number)}"
            )

        artifacts = dict(self.phase_artifacts.get(phase_number, {}))

        # Apply HITL edits if provided
        if edited_artifacts:
            for name, edited_content in edited_artifacts.items():
                try:
                    artifact_type = ArtifactType(name)
                    if artifact_type in artifacts:
                        LOG.info(
                            f"  HITL edit applied: {name} "
                            f"({len(artifacts[artifact_type])} -> {len(edited_content)} chars)"
                        )
                        artifacts[artifact_type] = edited_content
                        # Also update generator cache so downstream phases use the edit
                        if self._generator:
                            self._generator.cache.set(artifact_type, edited_content)
                except ValueError:
                    LOG.warning(f"  Ignoring unknown artifact in edits: {name}")

        # Create snapshot (convert ArtifactType keys to string keys)
        artifacts_dict = {at.value: content for at, content in artifacts.items()}
        snapshot = create_snapshot(
            phase_number=phase_number,
            artifacts_dict=artifacts_dict,
            approved_by=approved_by,
            notes=notes,
        )

        # Save snapshot to disk
        snapshot_dir = self.snapshot_base_dir / f"phase_{phase_number}"
        save_snapshot_to_disk(snapshot, snapshot_dir)

        # Also save transcript in the first phase snapshot
        if phase_number == 1:
            transcript_path = snapshot_dir / "questionnaire_transcript.md"
            transcript_path.write_text(self.raw_transcript, encoding="utf-8")

        # Update state
        self.snapshots[phase_number] = snapshot
        self.phase_statuses[phase_number] = PhaseStatus.APPROVED

        LOG.info(
            f"Phase {phase_number} approved by {approved_by}: "
            f"{len(artifacts_dict)} artifacts, snapshot at {snapshot_dir}"
        )

        return snapshot

    def reject_phase(self, phase_number: int, feedback: str):
        """
        Reject a phase with feedback. Allows re-generation.
        """
        if self.phase_statuses.get(phase_number) != PhaseStatus.REVIEW:
            raise ValueError(
                f"Phase {phase_number} is not in review state. "
                f"Current: {self.phase_statuses.get(phase_number)}"
            )

        self.phase_statuses[phase_number] = PhaseStatus.REJECTED
        self.phase_feedback[phase_number] = feedback

        # Clear the phase's artifacts from generator cache so they regenerate
        phase_def = get_phase_definition(phase_number)
        if self._generator:
            for artifact_type in phase_def.artifacts:
                self._generator.cache.remove(artifact_type)

        # Clear stored artifacts
        self.phase_artifacts.pop(phase_number, None)

        LOG.info(f"Phase {phase_number} rejected: {feedback[:100]}...")

    def get_snapshot(self, phase_number: int) -> Optional[PhaseSnapshot]:
        """Get approved snapshot for a phase."""
        return self.snapshots.get(phase_number)

    def get_all_approved_artifacts(self) -> Dict[ArtifactType, str]:
        """Collect all artifacts from all approved phases."""
        all_artifacts = {}
        for pn in sorted(self.snapshots.keys()):
            snap = self.snapshots[pn]
            for name, content in snap.artifacts.items():
                try:
                    all_artifacts[ArtifactType(name)] = content
                except ValueError:
                    pass
        return all_artifacts

    def get_phase_status(self, phase_number: int) -> PhaseStatus:
        """Get current status of a phase."""
        return self.phase_statuses.get(phase_number, PhaseStatus.PENDING)

    def get_editable_artifacts(self, phase_number: int) -> List[str]:
        """
        Return list of artifact names that support HITL editing for the given phase.

        For modernization at Phase 1, CAPABILITIES is editable (maturity ratings).
        """
        editable = []
        if phase_number == 1 and self.flow_type == FlowType.MODERNIZATION:
            editable.append(ArtifactType.CAPABILITIES.value)
        # PRD is always editable
        if phase_number == 1:
            editable.append(ArtifactType.PRD.value)
        return editable
