"""
Questionnaire Module - JSON loader, validator, and mapping-driven serializer.

Loads guided intake questionnaires from questionnaire/{flow_type}.json at runtime,
validates user answers, and produces structured prompt context using the `mapping`
field on each question.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

LOG = logging.getLogger("prdgen.intake.questionnaire")

QUESTIONNAIRE_DIR = Path(__file__).parent.parent.parent / "questionnaire"

# Mapping hierarchy for structured context serialization.
# First segment of each dot-path maps to a markdown section header.
MAPPING_SECTIONS = {
    "current_state": "## Current State",
    "future_state": "## Future / Target State",
    "nfrs": "## Non-Functional Requirements",
    "constraints": "## Constraints",
    "scope": "## Scope",
    "migration": "## Migration Strategy",
    "delta": "## Delta Analysis (Current \u2192 Target)",
    "integrations": "## Integrations & Dependencies",
    "dependencies": "## Integrations & Dependencies",  # alias
    "risks": "## Risks",
    "open_questions": "## Open Questions",
    "objectives": "## Objectives & Success Metrics",
    "success_metrics": "## Objectives & Success Metrics",  # merged
    "personas": "## Personas & User Groups",
    "stakeholders": "## Stakeholders",
    "problem_statement": "## Problem / Opportunity",
    "non_goals": "## Non-Goals",
    "delivery_model": "## Delivery Model",
    "capabilities_current_seed": "## Current State",  # alias
    "capabilities_future_seed": "## Future / Target State",  # alias
    "target_state": "## Future / Target State",  # alias for target_state.*
    "current_state.team": "## People & Org",
    "assumptions": "## Assumptions",
}


def load_questionnaire(flow_type: str) -> dict:
    """Load questionnaire JSON from questionnaire/{flow_type}.json at runtime."""
    json_path = QUESTIONNAIRE_DIR / f"{flow_type}.json"
    if not json_path.exists():
        raise FileNotFoundError(
            f"Questionnaire not found: {json_path}. "
            f"Valid flow types: {[f.stem for f in QUESTIONNAIRE_DIR.glob('*.json')]}"
        )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    LOG.info(f"Loaded questionnaire: {flow_type} (v{data.get('version', '?')})")
    return data


def get_questions(flow_type: str) -> List[dict]:
    """Return flat list of question dicts for the given flow type."""
    data = load_questionnaire(flow_type)
    questions = []
    for section in data.get("sections", []):
        for q in section.get("questions", []):
            # Attach section_title for display
            q["section_title"] = section.get("title", "")
            questions.append(q)
    return questions


def get_sections(flow_type: str) -> List[dict]:
    """Return list of section dicts with their questions."""
    data = load_questionnaire(flow_type)
    return data.get("sections", [])


def validate_answers(flow_type: str, answers: Dict[str, str]) -> List[str]:
    """
    Validate answers against schema (required fields, input types).
    Returns list of error strings (empty = valid).
    """
    questions = get_questions(flow_type)
    errors = []
    question_map = {q["id"]: q for q in questions}

    for q in questions:
        qid = q["id"]
        is_required = q.get("required", False)
        answer = answers.get(qid, "").strip()

        if is_required and not answer:
            errors.append(f"Required question '{qid}' ({q['question_text'][:60]}...) is unanswered.")

        if answer and q.get("input_type") == "single_select":
            options = q.get("options", [])
            if options and answer not in options:
                errors.append(
                    f"Question '{qid}': answer '{answer}' not in valid options {options}."
                )

    # Warn about unexpected answer keys
    valid_ids = set(question_map.keys())
    for key in answers:
        if key not in valid_ids:
            errors.append(f"Unknown question ID: '{key}' (not in questionnaire).")

    return errors


def _get_section_header(mapping_path: str) -> str:
    """
    Derive the markdown section header from a dot-notation mapping path.

    Examples:
        "current_state.architecture.summary" -> "## Current State"
        "nfrs.availability" -> "## Non-Functional Requirements"
        "risks" -> "## Risks"
    """
    # Check full path first (for specific overrides like "current_state.team")
    if mapping_path in MAPPING_SECTIONS:
        return MAPPING_SECTIONS[mapping_path]

    # Then check first segment
    first_segment = mapping_path.split(".")[0]
    return MAPPING_SECTIONS.get(first_segment, f"## {first_segment.replace('_', ' ').title()}")


def _get_subsection(mapping_path: str) -> Optional[str]:
    """
    Derive an optional subsection from deeper dot-path segments.

    Examples:
        "current_state.architecture.summary" -> "### Architecture"
        "nfrs.availability" -> "### Availability"
        "risks" -> None (no subsection)
        "objectives" -> None
    """
    parts = mapping_path.split(".")
    # Skip first segment (it's the section) and skip if it's just one level
    if len(parts) < 2:
        return None
    # Use second segment as subsection
    subsection = parts[1].replace("_", " ").title()
    return f"### {subsection}"


def format_answers_as_context(flow_type: str, answers: Dict[str, str]) -> str:
    """
    Produce the STRUCTURED context block for LLM prompt injection.

    Uses the `mapping` field to build a nested markdown document:
    - All `current_state.*` answers grouped under `## Current State`
    - All `nfrs.*` under `## Non-Functional Requirements`
    - Multi-mapped answers appear in EACH section they map to.

    Returns:
        Structured markdown string ready for LLM consumption.
    """
    questions = get_questions(flow_type)
    question_map = {q["id"]: q for q in questions}

    # Build: section_header -> subsection -> list of (question_text, answer)
    sections: Dict[str, Dict[Optional[str], List[tuple]]] = defaultdict(lambda: defaultdict(list))

    for qid, answer in answers.items():
        answer = answer.strip()
        if not answer:
            continue
        q = question_map.get(qid)
        if not q:
            continue

        mappings = q.get("mapping", [])
        if not mappings:
            # Fallback: use question section
            header = f"## {q.get('section', 'General').title()}"
            sections[header][None].append((q["question_text"], answer))
            continue

        for mp in mappings:
            header = _get_section_header(mp)
            subsection = _get_subsection(mp)
            sections[header][None if subsection is None else subsection].append(
                (q["question_text"], answer)
            )

    # Render markdown
    # Define preferred section order
    section_order = [
        "## Problem / Opportunity",
        "## Personas & User Groups",
        "## Current State",
        "## Future / Target State",
        "## Delta Analysis (Current \u2192 Target)",
        "## Objectives & Success Metrics",
        "## Scope",
        "## Non-Functional Requirements",
        "## Constraints",
        "## Migration Strategy",
        "## Integrations & Dependencies",
        "## People & Org",
        "## Stakeholders",
        "## Delivery Model",
        "## Non-Goals",
        "## Risks",
        "## Open Questions",
        "## Assumptions",
    ]

    lines = ["# Intake Context\n"]

    # Render ordered sections first, then any remaining
    rendered_sections = set()
    for section_header in section_order:
        if section_header in sections:
            rendered_sections.add(section_header)
            lines.append(f"\n{section_header}\n")
            _render_section_content(sections[section_header], lines)

    # Render any sections not in the predefined order
    for section_header in sorted(sections.keys()):
        if section_header not in rendered_sections:
            lines.append(f"\n{section_header}\n")
            _render_section_content(sections[section_header], lines)

    return "\n".join(lines).strip() + "\n"


def _render_section_content(
    subsections: Dict[Optional[str], List[tuple]],
    lines: List[str],
):
    """Render subsection content into lines list."""
    # Render None-keyed (no subsection) entries first
    if None in subsections:
        for question_text, answer in subsections[None]:
            lines.append(f"{answer}\n")

    # Render named subsections
    for subsection_header in sorted(k for k in subsections if k is not None):
        lines.append(f"\n{subsection_header}\n")
        for question_text, answer in subsections[subsection_header]:
            lines.append(f"{answer}\n")


def format_answers_as_transcript(flow_type: str, answers: Dict[str, str]) -> str:
    """
    Produce the RAW Q&A transcript for audit/traceability.

    Preserves original question order with section headers.
    Saved to snapshot but NOT fed to prompts.
    """
    data = load_questionnaire(flow_type)
    lines = [
        f"# Questionnaire Transcript: {data.get('title', flow_type)}\n",
        f"**Flow Type:** {flow_type}",
        f"**Version:** {data.get('version', 'unknown')}\n",
        "---\n",
    ]

    for section in data.get("sections", []):
        lines.append(f"\n## {section['title']}\n")
        for q in section.get("questions", []):
            qid = q["id"]
            answer = answers.get(qid, "").strip()
            required_tag = " *(required)*" if q.get("required") else ""
            lines.append(f"**Q: {q['question_text']}**{required_tag}\n")
            if answer:
                lines.append(f"**A:** {answer}\n")
            else:
                lines.append(f"**A:** *(not answered)*\n")

    return "\n".join(lines).strip() + "\n"


def get_questionnaire_version(flow_type: str) -> str:
    """Return the version string from the questionnaire JSON."""
    data = load_questionnaire(flow_type)
    return data.get("version", "unknown")
