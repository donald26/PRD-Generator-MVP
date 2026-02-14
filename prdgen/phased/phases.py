"""
Phase Definitions Module

Defines the 3 HITL phase gates, artifact-to-phase mapping, snapshot creation
with SHA-256 integrity hashing, and approval state machine.
"""
import hashlib
import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from ..artifact_types import ArtifactType, ARTIFACT_FILENAMES

LOG = logging.getLogger("prdgen.phased.phases")


class PhaseStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    REVIEW = "review"           # waiting for HITL approval
    APPROVED = "approved"
    REJECTED = "rejected"       # user sent it back with feedback


@dataclass
class PhaseDefinition:
    number: int                             # 1, 2, 3
    name: str                               # "Foundation", "Planning", "Detail"
    label: str                              # User-facing label
    artifacts: List[ArtifactType]           # Which artifacts this phase generates
    requires_phase: Optional[int] = None    # Previous phase that must be approved


@dataclass
class PhaseSnapshot:
    phase_number: int
    artifacts: Dict[str, str]               # artifact_name -> content (frozen)
    content_hashes: Dict[str, str]          # artifact_name -> SHA-256
    created_at: str = ""
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


# Phase Definitions - the 3 HITL gates
PHASE_DEFINITIONS = [
    PhaseDefinition(
        number=1,
        name="Foundation",
        label="Context Summary + PRD + Capabilities",
        artifacts=[
            ArtifactType.CONTEXT_SUMMARY,
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD,
            ArtifactType.CAPABILITIES,
        ],
        requires_phase=None,
    ),
    PhaseDefinition(
        number=2,
        name="Planning",
        label="Epics + Features + Roadmap",
        artifacts=[
            ArtifactType.CAPABILITY_CARDS,
            ArtifactType.EPICS,
            ArtifactType.FEATURES,
            ArtifactType.ROADMAP,
        ],
        requires_phase=1,
    ),
    PhaseDefinition(
        number=3,
        name="Detail",
        label="User Stories + Architecture",
        artifacts=[
            ArtifactType.USER_STORIES,
            ArtifactType.TECHNICAL_ARCHITECTURE,
            ArtifactType.LEAN_CANVAS,
        ],
        requires_phase=2,
    ),
]


def get_phase_definition(phase_number: int) -> PhaseDefinition:
    """Get phase definition by number (1, 2, or 3)."""
    for pd in PHASE_DEFINITIONS:
        if pd.number == phase_number:
            return pd
    raise ValueError(f"Invalid phase number: {phase_number}. Must be 1, 2, or 3.")


def get_phase_for_artifact(artifact_type: ArtifactType) -> Optional[int]:
    """Return which phase an artifact belongs to, or None if not in any phase."""
    for pd in PHASE_DEFINITIONS:
        if artifact_type in pd.artifacts:
            return pd.number
    return None


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_snapshot(
    phase_number: int,
    artifacts_dict: Dict[str, str],
    approved_by: Optional[str] = None,
    notes: Optional[str] = None,
) -> PhaseSnapshot:
    """
    Create a signed-off phase snapshot.

    Args:
        phase_number: Phase number (1, 2, or 3)
        artifacts_dict: Mapping of artifact_name -> content
        approved_by: Who approved (user email/id)
        notes: Optional approval notes

    Returns:
        PhaseSnapshot with SHA-256 content hashes
    """
    content_hashes = {
        name: compute_content_hash(content)
        for name, content in artifacts_dict.items()
    }

    now = datetime.now(timezone.utc).isoformat()

    return PhaseSnapshot(
        phase_number=phase_number,
        artifacts=dict(artifacts_dict),  # defensive copy
        content_hashes=content_hashes,
        created_at=now,
        approved_at=now if approved_by else None,
        approved_by=approved_by,
        notes=notes,
    )


def verify_snapshot(snapshot: PhaseSnapshot) -> bool:
    """
    Re-hash snapshot artifacts and verify integrity.

    Returns:
        True if all hashes match, False if any content was tampered with.
    """
    for name, content in snapshot.artifacts.items():
        expected_hash = snapshot.content_hashes.get(name)
        if expected_hash is None:
            LOG.warning(f"Missing hash for artifact: {name}")
            return False
        actual_hash = compute_content_hash(content)
        if actual_hash != expected_hash:
            LOG.warning(
                f"Hash mismatch for {name}: "
                f"expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
            )
            return False
    return True


def save_snapshot_to_disk(snapshot: PhaseSnapshot, snapshot_dir: Path) -> Path:
    """
    Freeze snapshot artifacts to disk.

    Creates:
        snapshot_dir/
            {artifact_name}.md   (for each artifact)
            snapshot_meta.json   (hashes, timestamps, approval info)

    Returns:
        Path to snapshot directory
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Write each artifact
    for name, content in snapshot.artifacts.items():
        # Use ARTIFACT_FILENAMES if available, else default
        filename = None
        for at, fn in ARTIFACT_FILENAMES.items():
            if at.value == name:
                filename = fn
                break
        if filename is None:
            filename = f"{name}.md"

        (snapshot_dir / filename).write_text(content, encoding="utf-8")

    # Write metadata
    meta = {
        "phase_number": snapshot.phase_number,
        "content_hashes": snapshot.content_hashes,
        "created_at": snapshot.created_at,
        "approved_at": snapshot.approved_at,
        "approved_by": snapshot.approved_by,
        "notes": snapshot.notes,
        "artifact_names": list(snapshot.artifacts.keys()),
    }
    (snapshot_dir / "snapshot_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    LOG.info(f"Saved phase {snapshot.phase_number} snapshot to {snapshot_dir}")
    return snapshot_dir


def load_snapshot_from_disk(snapshot_dir: Path) -> PhaseSnapshot:
    """
    Load a frozen snapshot from disk.

    Args:
        snapshot_dir: Directory containing snapshot files

    Returns:
        PhaseSnapshot loaded from disk

    Raises:
        FileNotFoundError: If snapshot_meta.json is missing
    """
    meta_path = snapshot_dir / "snapshot_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Snapshot metadata not found: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # Load artifact content
    artifacts = {}
    for name in meta.get("artifact_names", []):
        filename = None
        for at, fn in ARTIFACT_FILENAMES.items():
            if at.value == name:
                filename = fn
                break
        if filename is None:
            filename = f"{name}.md"

        file_path = snapshot_dir / filename
        if file_path.exists():
            artifacts[name] = file_path.read_text(encoding="utf-8")
        else:
            LOG.warning(f"Snapshot artifact file missing: {file_path}")

    return PhaseSnapshot(
        phase_number=meta["phase_number"],
        artifacts=artifacts,
        content_hashes=meta.get("content_hashes", {}),
        created_at=meta.get("created_at", ""),
        approved_at=meta.get("approved_at"),
        approved_by=meta.get("approved_by"),
        notes=meta.get("notes"),
    )


def get_prior_snapshots(
    phase_number: int,
    session_snapshots: Dict[int, PhaseSnapshot],
) -> Dict[str, str]:
    """
    Collect all artifacts from prior approved phases.

    Used to seed the generator cache before running a new phase.

    Args:
        phase_number: The phase about to run
        session_snapshots: Map of phase_number -> approved PhaseSnapshot

    Returns:
        Flat dict of artifact_name -> content from all prior phases
    """
    prior_artifacts = {}
    for pn in range(1, phase_number):
        snap = session_snapshots.get(pn)
        if snap is None:
            raise ValueError(f"Phase {pn} snapshot required but not found.")
        if not verify_snapshot(snap):
            raise ValueError(f"Phase {pn} snapshot integrity check failed.")
        prior_artifacts.update(snap.artifacts)
    return prior_artifacts
