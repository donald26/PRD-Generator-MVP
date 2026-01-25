"""
Artifact dependency resolution and caching.
Ensures required artifacts are generated even if not explicitly selected.
"""
from typing import Set, List, Dict, Optional
from pathlib import Path
import logging

from .artifact_types import ArtifactType, ARTIFACT_FILENAMES

LOG = logging.getLogger("prdgen.dependencies")

class ArtifactDependencyResolver:
    """Manages artifact dependencies and generation order"""

    # Dependency graph: artifact -> list of required predecessors
    DEPENDENCIES: Dict[ArtifactType, List[ArtifactType]] = {
        ArtifactType.CORPUS_SUMMARY: [],
        ArtifactType.PRD: [ArtifactType.CORPUS_SUMMARY],
        ArtifactType.CAPABILITIES: [
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD
        ],
        ArtifactType.CAPABILITY_CARDS: [
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD,
            ArtifactType.CAPABILITIES
        ],
        ArtifactType.EPICS: [
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD,
            ArtifactType.CAPABILITIES,
            ArtifactType.CAPABILITY_CARDS
        ],
        ArtifactType.FEATURES: [
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD,
            ArtifactType.EPICS
        ],
        ArtifactType.USER_STORIES: [
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD,
            ArtifactType.EPICS,
            ArtifactType.FEATURES
        ],
        ArtifactType.LEAN_CANVAS: [
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD,
            ArtifactType.CAPABILITIES
        ],
    }

    # Canonical generation order (topologically sorted)
    GENERATION_ORDER: List[ArtifactType] = [
        ArtifactType.CORPUS_SUMMARY,
        ArtifactType.PRD,
        ArtifactType.CAPABILITIES,
        ArtifactType.CAPABILITY_CARDS,
        ArtifactType.EPICS,
        ArtifactType.FEATURES,
        ArtifactType.USER_STORIES,
        ArtifactType.LEAN_CANVAS,
    ]

    @classmethod
    def resolve(cls, selected: Set[ArtifactType]) -> List[ArtifactType]:
        """
        Resolve dependencies and return ordered list of artifacts to generate.

        Args:
            selected: Set of explicitly selected artifacts

        Returns:
            List of artifacts in generation order (includes dependencies)

        Example:
            selected = {ArtifactType.FEATURES}
            returns = [CORPUS_SUMMARY, PRD, EPICS, FEATURES]
        """
        required = set()

        def add_with_deps(artifact: ArtifactType):
            """Recursively add artifact and its dependencies"""
            if artifact in required:
                return
            # Add dependencies first (recursive)
            for dep in cls.DEPENDENCIES[artifact]:
                add_with_deps(dep)
            required.add(artifact)

        # Add all selected artifacts with their dependencies
        for artifact in selected:
            add_with_deps(artifact)

        # Return in canonical generation order
        result = [a for a in cls.GENERATION_ORDER if a in required]

        LOG.info(f"Dependency resolution: {len(selected)} selected -> {len(result)} to generate")
        LOG.debug(f"Selected: {[a.value for a in selected]}")
        LOG.debug(f"To generate: {[a.value for a in result]}")

        return result

    @classmethod
    def get_direct_dependencies(cls, artifact: ArtifactType) -> List[ArtifactType]:
        """Get direct dependencies for a specific artifact"""
        return cls.DEPENDENCIES.get(artifact, [])

    @classmethod
    def is_dependent_on(cls, artifact: ArtifactType, dependency: ArtifactType) -> bool:
        """Check if artifact depends on dependency (directly or transitively)"""
        deps = cls.resolve({artifact})
        return dependency in deps


class ArtifactCache:
    """
    Manages caching of previously generated artifacts.
    Allows resuming from existing artifacts to save time.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize artifact cache.

        Args:
            cache_dir: Directory to load cached artifacts from (None = no disk cache)
        """
        self.cache_dir = cache_dir
        self.cache: Dict[ArtifactType, str] = {}

    def load_from_disk(self):
        """Load existing artifacts from cache directory"""
        if not self.cache_dir or not self.cache_dir.exists():
            LOG.debug("No cache directory available")
            return

        loaded_count = 0
        for artifact_type, filename in ARTIFACT_FILENAMES.items():
            file_path = self.cache_dir / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if content.strip():  # Only cache non-empty files
                        self.cache[artifact_type] = content
                        loaded_count += 1
                        LOG.debug(f"Loaded cached artifact: {artifact_type.value}")
                except Exception as e:
                    LOG.warning(f"Failed to load cached artifact {filename}: {e}")

        if loaded_count > 0:
            LOG.info(f"Loaded {loaded_count} cached artifacts from {self.cache_dir}")

    def get(self, artifact_type: ArtifactType) -> Optional[str]:
        """Get cached artifact if available"""
        return self.cache.get(artifact_type)

    def set(self, artifact_type: ArtifactType, content: str):
        """Cache an artifact in memory"""
        self.cache[artifact_type] = content

    def has(self, artifact_type: ArtifactType) -> bool:
        """Check if artifact is cached"""
        return artifact_type in self.cache

    def get_available_artifacts(self) -> Set[ArtifactType]:
        """Return set of cached artifact types"""
        return set(self.cache.keys())

    def clear(self):
        """Clear all cached artifacts"""
        self.cache.clear()

    def remove(self, artifact_type: ArtifactType):
        """Remove specific artifact from cache"""
        self.cache.pop(artifact_type, None)

    def __len__(self) -> int:
        """Return number of cached artifacts"""
        return len(self.cache)

    def __contains__(self, artifact_type: ArtifactType) -> bool:
        """Support 'in' operator"""
        return self.has(artifact_type)
