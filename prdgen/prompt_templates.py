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
- Avoid vague acceptance criteria (e.g., "works correctly", "fast enough")."""
    }

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize prompt template manager.

        Args:
            template_dir: Directory containing template files (default: ../templates)
        """
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self._templates: Dict[str, str] = {}
        self._load_templates()

    def _load_templates(self):
        """Load artifact templates from template directory"""
        if not self.template_dir.exists():
            LOG.warning(f"Template directory not found: {self.template_dir}")
            return

        template_files = {
            "epic": "Epic_Template.md",
            "feature": "Feature_Template.md",
            "user_story": "User_Story_Template.md"
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

    def get_system_prompt(self, artifact_type: str) -> str:
        """
        Get system prompt for an artifact type.

        Args:
            artifact_type: One of: context, summary, prd, features, capabilities, canvas, stories

        Returns:
            System prompt string
        """
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
        """Create instance with default template directory"""
        return cls(DEFAULT_TEMPLATE_DIR)


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
