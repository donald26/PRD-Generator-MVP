"""
Roadmap validation and parsing utilities.
"""
import re
from typing import List, Dict, Optional


def validate_roadmap_structure(md: str) -> bool:
    """Check that roadmap markdown has required sections."""
    required_patterns = [
        r"##\s+.*(?:MVP|Phase\s+1|Wave\s+1)",  # At least one phase
        r"EP-\d+",  # At least one epic reference
    ]
    for pattern in required_patterns:
        if not re.search(pattern, md, flags=re.IGNORECASE):
            return False
    return True


def extract_phases_from_roadmap(md: str) -> List[Dict[str, str]]:
    """
    Extract phase blocks from roadmap markdown.

    Returns list of dicts with 'name', 'scope', 'epics' keys.
    """
    phases = []
    # Match ### Phase/Wave headers
    phase_pattern = re.compile(
        r"^###\s+(.+)$", flags=re.MULTILINE
    )
    matches = list(phase_pattern.finditer(md))

    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        content = md[start:end].strip()

        # Extract epic references
        epics = re.findall(r"EP-\d+", content)

        phases.append({
            "name": name,
            "content": content,
            "epics": list(dict.fromkeys(epics)),  # dedupe preserving order
        })

    return phases


def extract_dependency_map(md: str) -> List[Dict[str, Optional[str]]]:
    """Extract dependency table rows from roadmap markdown."""
    deps = []
    # Match table rows like: | EP-001 | EP-002 | EP-003 | Yes |
    row_pattern = re.compile(
        r"\|\s*(EP-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(Yes|No)\s*\|",
        flags=re.IGNORECASE,
    )
    for match in row_pattern.finditer(md):
        deps.append({
            "epic": match.group(1).strip(),
            "depends_on": match.group(2).strip() or None,
            "blocking": match.group(3).strip() or None,
            "critical_path": match.group(4).strip().lower() == "yes",
        })
    return deps
