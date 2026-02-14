"""
Prompt Template Management System

This module manages system prompts and artifact templates, loading them from
configuration and template files to ensure consistency and maintainability.
"""
import logging
from pathlib import Path
from typing import Dict, Optional

LOG = logging.getLogger("prdgen.prompt_templates")

# Default template directory (relative to this file)
DEFAULT_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

# System prompt directory for file-based prompts (relative to this file)
SYSTEM_PROMPT_DIR = Path(__file__).parent.parent / "prompts" / "system"


class PromptTemplates:
    """Manages system prompts and artifact templates"""

    # Improved system prompts with strict hallucination prevention
    SYSTEM_PROMPTS = {
        "context": """You are a Senior Product Analyst performing comprehensive document analysis.

Rules:
- Extract ONLY information explicitly stated in the provided documents.
- Do NOT infer intent, add assumptions, or fill gaps.
- If information is unclear, conflicting, or missing, explicitly flag it as such.
- Use concise, factual language.
- Do not add recommendations or opinions.

Output requirements:
- Organize findings into clear sections.
- Distinguish clearly between:
  * Explicit statements
  * Ambiguities
  * Missing information""",

        "summary": """You summarize multiple product documents faithfully and objectively.

Rules:
- Base the summary ONLY on explicitly stated content.
- Do NOT introduce new facts, interpretations, or assumptions.
- If the documents do not provide sufficient information for a section, state "Not specified in source documents".
- Preserve uncertainty and disagreement when present.

Output requirements:
- Structured summary with consistent sections.
- Neutral, analytical tone.
- No speculative or promotional language.""",

        "prd": """You produce a high-quality Product Requirements Document (PRD).

Rules:
- Follow the provided PRD outline exactly.
- Populate sections ONLY with information grounded in the document summary.
- Do NOT invent requirements, scope, timelines, or success metrics.
- If a required PRD section lacks source data, explicitly state that it is undefined.

Quality constraints:
- Use clear, deterministic language.
- Avoid vague terms such as "optimize", "seamless", or "improve" unless explicitly stated in the source.""",

        "features": """You produce structured feature definitions derived strictly from the PRD and associated epics.

Rules:
- Each feature must map clearly to a PRD requirement or epic.
- Do NOT introduce new functionality not present in the PRD.
- Do NOT restate PRD text verbatim; abstract to feature-level behavior.
- If feature boundaries are unclear, flag them explicitly.

Output requirements:
- Consistent structure across all features.
- Clear linkage to epics and PRD sections.""",

        "capabilities": """You produce a capability map derived strictly from the PRD.

Rules:
- Capabilities must represent WHAT the system must be able to do, not HOW it is implemented.
- Derive capabilities only from explicitly stated requirements.
- Do NOT introduce solution-specific or technical design elements unless stated in the PRD.
- Organize capabilities hierarchically (L1–L3 where applicable).
- If information is insufficient to define lower-level capabilities, stop at the appropriate level.""",

        "canvas": """You produce a Lean Canvas derived strictly from the PRD and capability map.

Rules:
- Populate each canvas section only if supported by PRD or capability content.
- Do NOT invent customer segments, revenue streams, or value propositions.
- If a canvas section is not supported by source material, mark it as "Not defined".

Tone:
- Factual and analytical
- No marketing or aspirational language""",

        "stories": """You produce detailed user stories derived strictly from defined features.

Rules:
- Each story must map to a specific feature.
- Use Gherkin-style acceptance criteria.
- Do NOT introduce new business rules or edge cases not described in the feature.
- If acceptance criteria cannot be fully defined, explicitly state the missing inputs.

Quality constraints:
- Stories must be testable and unambiguous.
- Avoid vague acceptance criteria (e.g., "works correctly", "fast enough").""",

        "capabilities_modernization": """You produce a modernization capability assessment framework derived from the PRD and intake context.

Rules:
- Derive transformation pillars from the domain described in the documents.
  Do NOT use generic/fixed pillar names -- they must reflect the actual
  business domain being modernized.
- For Current State: base descriptions on explicit pain points, constraints,
  and current-system descriptions from the input documents.
- For Maturity ratings: use ONLY these four levels:
  Non-Existent, Lagging, On Par, Leading.
- For Desired Future State: derive from goals, vision, and desired outcomes
  in the documents. Do NOT invent aspirations not supported by the inputs.
- If information is insufficient to rate a capability, mark maturity as
  "Unknown" and flag in the Gap Summary.
- Include Part 3 (Gap Summary) to highlight the biggest current-to-target deltas.

Output requirements:
- Follow the Capability Assessment Template structure exactly.
- All three parts (Pillar Overview, Detailed Assessment, Gap Summary) are required.""",

        "roadmap": """You produce a delivery roadmap derived strictly from the PRD, epics, and features.

Rules:
- Organize delivery into release phases (MVP / Phase 1 / Phase 2 / Phase 3+).
- Map each epic to a phase with rationale for sequencing.
- Identify dependencies and critical path items.
- Include risk-adjusted timeline considerations.
- Do NOT invent delivery dates or team sizes not present in the inputs.
- If timeline info is missing, use relative sequencing only.

Output requirements:
- Structured markdown with phase-by-phase breakdown.
- Dependency diagram or table showing epic relationships.
- Clear MVP scope definition.""",

        "architecture": """You are a Solutions Architect creating technical architecture documentation.

Rules:
- Derive architecture ONLY from explicitly stated requirements and capabilities.
- Do NOT invent components, services, or technologies not implied by the inputs.
- If information is insufficient to specify a component detail, mark it as "Not specified".
- Use standard architectural patterns appropriate to the domain.
- Include AI/ML components (model runtime, RAG, vector DB) ONLY if explicitly mentioned.

Output requirements:
- Produce structured architecture with components, data flows, and NFRs.
- Include a Mermaid diagram using flowchart TB (top-bottom) notation.
- Group components into subgraphs: Client, Core Platform, Data Layer, AI Layer (if applicable), External Integrations.
- Flag assumptions and open questions explicitly.

Quality constraints:
- Component IDs must be unique, lowercase, underscore-separated (e.g., user_service).
- Data flows must reference valid component IDs.
- Mermaid syntax must be valid and render correctly."""
    }

    def __init__(self, template_dir: Optional[Path] = None, system_prompt_dir: Optional[Path] = None):
        """
        Initialize prompt template manager.

        Args:
            template_dir: Directory containing template files (default: ../templates)
            system_prompt_dir: Directory containing system prompt files (default: ../prompts/system)
        """
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self.system_prompt_dir = system_prompt_dir or SYSTEM_PROMPT_DIR
        self._templates: Dict[str, str] = {}
        self._file_prompts: Dict[str, str] = {}
        self._load_templates()
        self._load_system_prompts_from_files()

    def _load_templates(self):
        """Load artifact templates from template directory"""
        if not self.template_dir.exists():
            LOG.warning(f"Template directory not found: {self.template_dir}")
            return

        template_files = {
            "epic": "Epic_Template.md",
            "feature": "Feature_Template.md",
            "user_story": "User_Story_Template.md",
            "capability_assessment": "Capability_Assessment_Template.md",
            "capability_card_modernization": "Capability_Card_Modernization_Template.md",
        }

        for key, filename in template_files.items():
            template_path = self.template_dir / filename
            if template_path.exists():
                try:
                    self._templates[key] = template_path.read_text(encoding='utf-8')
                    LOG.debug(f"Loaded {key} template from {filename}")
                except Exception as e:
                    LOG.warning(f"Failed to load {filename}: {e}")
            else:
                LOG.warning(f"Template file not found: {filename}")

    def _load_system_prompts_from_files(self):
        """
        Load system prompts from the prompts/system/ directory.

        Files are named {artifact_type}.txt and take precedence over
        hardcoded SYSTEM_PROMPTS for runtime configurability.
        """
        if not self.system_prompt_dir.exists():
            LOG.debug(f"System prompt directory not found: {self.system_prompt_dir}")
            return

        # Load all .txt files as system prompts
        for prompt_file in self.system_prompt_dir.glob("*.txt"):
            artifact_type = prompt_file.stem  # filename without extension
            try:
                content = prompt_file.read_text(encoding='utf-8').strip()
                if content:
                    self._file_prompts[artifact_type] = content
                    LOG.info(f"Loaded system prompt from file: {artifact_type}.txt")
            except Exception as e:
                LOG.warning(f"Failed to load system prompt {prompt_file.name}: {e}")

    def get_system_prompt_from_file(self, artifact_type: str) -> Optional[str]:
        """
        Get system prompt loaded from file, if available.

        Args:
            artifact_type: The artifact type (e.g., 'architecture')

        Returns:
            System prompt string or None if not found in files
        """
        return self._file_prompts.get(artifact_type)

    def has_system_prompt_file(self, artifact_type: str) -> bool:
        """Check if a file-based system prompt exists for the artifact type."""
        return artifact_type in self._file_prompts

    def get_system_prompt(self, artifact_type: str) -> str:
        """
        Get system prompt for an artifact type.

        Checks file-based prompts first (from prompts/system/{artifact_type}.txt),
        then falls back to hardcoded SYSTEM_PROMPTS.

        Args:
            artifact_type: One of: context, summary, prd, features, capabilities, canvas, stories, architecture

        Returns:
            System prompt string
        """
        # Priority 1: File-based prompts (runtime configurable)
        file_prompt = self._file_prompts.get(artifact_type)
        if file_prompt:
            LOG.debug(f"Using file-based system prompt for: {artifact_type}")
            return file_prompt

        # Priority 2: Hardcoded prompts (fallback)
        prompt = self.SYSTEM_PROMPTS.get(artifact_type)
        if not prompt:
            LOG.warning(f"No system prompt defined for: {artifact_type}")
            return f"You are a product management AI assistant generating {artifact_type}."
        return prompt

    def get_template(self, template_type: str) -> Optional[str]:
        """
        Get artifact template content.

        Args:
            template_type: One of: epic, feature, user_story

        Returns:
            Template content or None if not found
        """
        return self._templates.get(template_type)

    def has_template(self, template_type: str) -> bool:
        """Check if template is available"""
        return template_type in self._templates

    def get_template_structure(self, template_type: str) -> str:
        """
        Get a formatted version of the template structure for inclusion in prompts.

        Args:
            template_type: One of: epic, feature, user_story

        Returns:
            Formatted template structure description
        """
        template = self.get_template(template_type)
        if not template:
            return f"Standard {template_type} format"

        # Extract section headers from template
        lines = template.split('\n')
        sections = []
        for line in lines:
            if line.startswith('##'):
                # Extract section name (remove ## and trim)
                section = line.replace('##', '').strip()
                sections.append(f"- {section}")

        if sections:
            return f"Use this structure:\n" + "\n".join(sections)
        return template

    @classmethod
    def create_default(cls) -> 'PromptTemplates':
        """Create instance with default template and system prompt directories"""
        return cls(DEFAULT_TEMPLATE_DIR, SYSTEM_PROMPT_DIR)


# Global instance for convenience
_default_templates: Optional[PromptTemplates] = None


def get_default_templates() -> PromptTemplates:
    """Get or create the default templates instance"""
    global _default_templates
    if _default_templates is None:
        _default_templates = PromptTemplates.create_default()
    return _default_templates


def get_system_prompt(artifact_type: str) -> str:
    """Convenience function to get system prompt"""
    return get_default_templates().get_system_prompt(artifact_type)


def get_template(template_type: str) -> Optional[str]:
    """Convenience function to get template"""
    return get_default_templates().get_template(template_type)


def get_template_structure(template_type: str) -> str:
    """Convenience function to get template structure"""
    return get_default_templates().get_template_structure(template_type)


def get_system_prompt_from_file(artifact_type: str) -> Optional[str]:
    """Convenience function to get file-based system prompt"""
    return get_default_templates().get_system_prompt_from_file(artifact_type)


def has_system_prompt_file(artifact_type: str) -> bool:
    """Convenience function to check if file-based system prompt exists"""
    return get_default_templates().has_system_prompt_file(artifact_type)


def validate_system_prompt_file(artifact_type: str) -> bool:
    """
    Validate that a system prompt file exists and is loadable.

    Args:
        artifact_type: The artifact type to validate (e.g., 'architecture')

    Returns:
        True if the file exists and was loaded successfully

    Raises:
        FileNotFoundError: If the prompt file does not exist
        ValueError: If the prompt file is empty
    """
    prompt_path = SYSTEM_PROMPT_DIR / f"{artifact_type}.txt"

    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt file not found: {prompt_path}")

    content = prompt_path.read_text(encoding='utf-8').strip()
    if not content:
        raise ValueError(f"System prompt file is empty: {prompt_path}")

    # Verify it's loaded in the cache
    templates = get_default_templates()
    if not templates.has_system_prompt_file(artifact_type):
        # Force reload
        templates._load_system_prompts_from_files()

    return templates.has_system_prompt_file(artifact_type)
