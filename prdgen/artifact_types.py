"""
Artifact type definitions and predefined sets for selective generation.
"""
from enum import Enum
from typing import Set, Dict

class ArtifactType(str, Enum):
    """Enumeration of all artifact types that can be generated"""
    CONTEXT_SUMMARY = "context_summary"  # NEW: First-stage document context assessment
    CORPUS_SUMMARY = "corpus_summary"
    PRD = "prd"
    CAPABILITIES = "capabilities"
    CAPABILITY_CARDS = "capability_cards"
    EPICS = "epics"
    FEATURES = "features"
    USER_STORIES = "user_stories"
    LEAN_CANVAS = "lean_canvas"
    TECHNICAL_ARCHITECTURE = "technical_architecture"

# Predefined artifact sets for common use cases
ARTIFACT_SETS: Dict[str, Set[ArtifactType]] = {
    "business": {  # DEFAULT per user request - fast business overview
        ArtifactType.CORPUS_SUMMARY,
        ArtifactType.PRD,
        ArtifactType.CAPABILITIES,
        ArtifactType.LEAN_CANVAS
    },
    "minimal": {  # Quickest - just the PRD
        ArtifactType.CORPUS_SUMMARY,
        ArtifactType.PRD
    },
    "development": {  # For dev teams - up to features
        ArtifactType.CORPUS_SUMMARY,
        ArtifactType.PRD,
        ArtifactType.CAPABILITIES,
        ArtifactType.CAPABILITY_CARDS,
        ArtifactType.EPICS,
        ArtifactType.FEATURES,
        ArtifactType.TECHNICAL_ARCHITECTURE,
    },
    "complete": {  # All artifacts
        ArtifactType.CORPUS_SUMMARY,
        ArtifactType.PRD,
        ArtifactType.CAPABILITIES,
        ArtifactType.CAPABILITY_CARDS,
        ArtifactType.EPICS,
        ArtifactType.FEATURES,
        ArtifactType.USER_STORIES,
        ArtifactType.LEAN_CANVAS,
        ArtifactType.TECHNICAL_ARCHITECTURE,
    }
}

# Human-readable names for UI display
ARTIFACT_NAMES: Dict[ArtifactType, str] = {
    ArtifactType.CONTEXT_SUMMARY: "Document Context Assessment",
    ArtifactType.CORPUS_SUMMARY: "Corpus Summary",
    ArtifactType.PRD: "Product Requirements Document",
    ArtifactType.CAPABILITIES: "Capability Map",
    ArtifactType.CAPABILITY_CARDS: "Capability Cards",
    ArtifactType.EPICS: "Epics",
    ArtifactType.FEATURES: "Features",
    ArtifactType.USER_STORIES: "User Stories",
    ArtifactType.LEAN_CANVAS: "Lean Canvas",
    ArtifactType.TECHNICAL_ARCHITECTURE: "Technical Architecture Reference",
}

# File names for each artifact
ARTIFACT_FILENAMES: Dict[ArtifactType, str] = {
    ArtifactType.CONTEXT_SUMMARY: "context_summary.md",
    ArtifactType.CORPUS_SUMMARY: "corpus_summary.md",
    ArtifactType.PRD: "prd.md",
    ArtifactType.CAPABILITIES: "capabilities.md",
    ArtifactType.CAPABILITY_CARDS: "capability_cards.md",
    ArtifactType.EPICS: "epics.md",
    ArtifactType.FEATURES: "features.md",
    ArtifactType.USER_STORIES: "user_stories.md",
    ArtifactType.LEAN_CANVAS: "lean_canvas.md",
    ArtifactType.TECHNICAL_ARCHITECTURE: "architecture_reference.md",
}

def get_artifact_set(name: str) -> Set[ArtifactType]:
    """
    Get a predefined artifact set by name.

    Args:
        name: Set name ("business", "minimal", "development", "complete")

    Returns:
        Set of artifact types

    Raises:
        ValueError: If set name is not recognized
    """
    if name not in ARTIFACT_SETS:
        raise ValueError(
            f"Unknown artifact set '{name}'. "
            f"Valid options: {', '.join(ARTIFACT_SETS.keys())}"
        )
    return ARTIFACT_SETS[name]

def validate_artifact_names(artifact_names: Set[str]) -> Set[ArtifactType]:
    """
    Validate artifact names and convert to ArtifactType enum.

    Args:
        artifact_names: Set of artifact name strings

    Returns:
        Set of validated ArtifactType enums

    Raises:
        ValueError: If any artifact name is invalid
    """
    validated = set()
    for name in artifact_names:
        try:
            validated.add(ArtifactType(name))
        except ValueError:
            valid_names = [a.value for a in ArtifactType]
            raise ValueError(
                f"Invalid artifact name '{name}'. "
                f"Valid options: {', '.join(valid_names)}"
            )
    return validated
