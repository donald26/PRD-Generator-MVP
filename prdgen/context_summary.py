"""
Context Summary utilities for parsing and formatting.

This module handles the Document Context Assessment artifact, which is the
first stage of the PRD generation pipeline.
"""
import re
import json
import logging
from typing import Dict, List, Any
from pathlib import Path

LOG = logging.getLogger("prdgen.context_summary")


def parse_context_summary_markdown(markdown: str) -> Dict[str, Any]:
    """
    Parse the generated context summary markdown into a structured JSON format.

    Args:
        markdown: The generated markdown context summary

    Returns:
        Dictionary with structured context information
    """
    result = {
        "problem_opportunity": "",
        "goals": [],
        "non_goals": [],
        "target_personas": [],
        "key_functional_requirements": [],
        "constraints_assumptions": {
            "technical_constraints": [],
            "business_constraints": [],
            "assumptions": []
        },
        "risks_gaps_questions": {
            "risks": [],
            "information_gaps": [],
            "open_questions": [],
            "conflicts": []
        },
        "source_traceability": {}
    }

    # Split into sections by headers
    sections = re.split(r'\n## ', markdown)

    for section in sections:
        if not section.strip():
            continue

        lines = section.split('\n')
        header = lines[0].strip()
        content_lines = [l.strip() for l in lines[1:] if l.strip()]

        # Problem / Opportunity
        if header.startswith("Problem") or header == "Problem / Opportunity":
            result["problem_opportunity"] = '\n'.join(content_lines)

        # Goals
        elif header == "Goals":
            result["goals"] = _extract_list_items(content_lines)

        # Non-Goals
        elif header == "Non-Goals":
            result["non_goals"] = _extract_list_items(content_lines)

        # Target Personas / Users
        elif "Personas" in header or "Users" in header:
            result["target_personas"] = _extract_list_items(content_lines)

        # Key Functional Requirements
        elif "Functional Requirements" in header:
            result["key_functional_requirements"] = _extract_list_items(content_lines)

        # Constraints & Assumptions
        elif "Constraints" in header and "Assumptions" in header:
            result["constraints_assumptions"] = _parse_constraints_section(content_lines)

        # Risks, Gaps, and Open Questions
        elif "Risks" in header and "Gaps" in header:
            result["risks_gaps_questions"] = _parse_risks_section(content_lines)

        # Source Traceability
        elif "Source Traceability" in header or "Traceability" in header:
            result["source_traceability"] = _parse_source_traceability(content_lines)

    return result


def _extract_list_items(lines: List[str]) -> List[str]:
    """Extract bullet points from markdown lines"""
    items = []
    for line in lines:
        # Match lines starting with - or * bullets
        match = re.match(r'^[-*]\s+(.+)$', line)
        if match:
            items.append(match.group(1).strip())
            continue

        # Match numbered lists (1. or 1))
        match = re.match(r'^\d+[\.\)]\s*(.+)$', line)
        if match:
            items.append(match.group(1).strip())
            continue

        # Non-list lines (but skip common "not specified" phrases and headers)
        if line and not line.startswith('#') and not line.startswith('**'):
            if line not in ["Not specified in documents", "None specified", "Not explicitly defined in documents"]:
                items.append(line)
    return items


def _parse_constraints_section(lines: List[str]) -> Dict[str, List[str]]:
    """Parse the Constraints & Assumptions section"""
    result = {
        "technical_constraints": [],
        "business_constraints": [],
        "assumptions": []
    }

    current_subsection = None

    for line in lines:
        if "**Technical Constraints:**" in line:
            current_subsection = "technical_constraints"
        elif "**Business Constraints:**" in line:
            current_subsection = "business_constraints"
        elif "**Assumptions:**" in line:
            current_subsection = "assumptions"
        elif line.startswith('-') or line.startswith('*'):
            if current_subsection:
                item = re.sub(r'^[-*]\s*', '', line).strip()
                if item and item not in ["None specified", "Not specified in documents"]:
                    result[current_subsection].append(item)

    return result


def _parse_risks_section(lines: List[str]) -> Dict[str, List[str]]:
    """Parse the Risks, Gaps, and Open Questions section"""
    result = {
        "risks": [],
        "information_gaps": [],
        "open_questions": [],
        "conflicts": []
    }

    current_subsection = None

    for line in lines:
        if "**Risks:**" in line:
            current_subsection = "risks"
        elif "**Information Gaps:**" in line:
            current_subsection = "information_gaps"
        elif "**Open Questions:**" in line:
            current_subsection = "open_questions"
        elif "**Conflicts:**" in line:
            current_subsection = "conflicts"
        elif line.startswith('-') or line.startswith('*'):
            if current_subsection:
                item = re.sub(r'^[-*]\s*', '', line).strip()
                if item and item not in ["None specified", "Not specified in documents", "None identified"]:
                    result[current_subsection].append(item)

    return result


def _parse_source_traceability(lines: List[str]) -> Dict[str, List[str]]:
    """Parse source traceability mappings"""
    traceability = {}

    for line in lines:
        # Match patterns like "**Problem/Opportunity:** [file1.docx, file2.md]"
        match = re.match(r'\*\*(.+?):\*\*\s*\[(.+?)\]', line)
        if match:
            key = match.group(1).strip().lower().replace('/', '_').replace(' ', '_')
            files = [f.strip() for f in match.group(2).split(',')]
            traceability[key] = files

    return traceability


def save_context_summary_json(context_dict: Dict[str, Any], output_path: Path) -> None:
    """
    Save the context summary as a JSON file.

    Args:
        context_dict: Structured context dictionary
        output_path: Path to save the JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(context_dict, f, indent=2, ensure_ascii=False)

    LOG.info(f"Saved context summary JSON to {output_path}")


def format_context_summary_for_consumption(context_dict: Dict[str, Any]) -> str:
    """
    Format context summary for consumption by downstream artifacts.

    This creates a clean, readable version that can be included in prompts
    for subsequent artifact generation.

    Args:
        context_dict: Structured context dictionary

    Returns:
        Formatted string suitable for including in prompts
    """
    lines = ["## Document Context Summary\n"]

    if context_dict.get("problem_opportunity"):
        lines.append(f"**Problem/Opportunity:** {context_dict['problem_opportunity']}\n")

    if context_dict.get("goals"):
        lines.append("**Goals:**")
        for goal in context_dict["goals"]:
            lines.append(f"- {goal}")
        lines.append("")

    if context_dict.get("non_goals"):
        lines.append("**Non-Goals:**")
        for ng in context_dict["non_goals"]:
            lines.append(f"- {ng}")
        lines.append("")

    if context_dict.get("target_personas"):
        lines.append("**Target Personas:**")
        for persona in context_dict["target_personas"]:
            lines.append(f"- {persona}")
        lines.append("")

    if context_dict.get("key_functional_requirements"):
        lines.append("**Key Requirements:**")
        for req in context_dict["key_functional_requirements"]:
            lines.append(f"- {req}")
        lines.append("")

    return '\n'.join(lines)
