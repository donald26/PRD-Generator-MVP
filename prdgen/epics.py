import re
from typing import List, Dict, Tuple

def extract_l0_l1_mapping(capabilities_md: str) -> Dict[str, str]:
    """
    Extract mapping of L1 capability names to their L0 domain.
    Returns: {L1_name: L0_name}
    """
    mapping = {}
    current_l0 = None

    for line in capabilities_md.split('\n'):
        l0_match = re.match(r'^#\s+L0:\s*(.+)$', line.strip())
        if l0_match:
            current_l0 = l0_match.group(1).strip()
            continue

        l1_match = re.match(r'^##\s+L1:\s*(.+)$', line.strip())
        if l1_match and current_l0:
            l1_name = l1_match.group(1).strip()
            mapping[l1_name] = current_l0

    return mapping

def extract_epic_ids(epics_md: str) -> List[str]:
    """
    Extract all Epic IDs from the generated epics markdown.
    Returns: List of epic IDs (e.g., ['EP-001', 'EP-002'])
    """
    epic_ids = re.findall(r'\*\*Epic ID\*\*:\s*(EP-\d+)', epics_md)
    return epic_ids

def extract_l1_from_epics(epics_md: str) -> List[str]:
    """
    Extract all L1 capability names that have epics.
    Returns: List of L1 names
    """
    # Look for **Capability**: [name] pattern
    capabilities = re.findall(r'\*\*Capability\*\*:\s*(.+)$', epics_md, flags=re.MULTILINE)
    # Also look for ## [L1 Name] headers
    headers = re.findall(r'^##\s+(.+)$', epics_md, flags=re.MULTILINE)

    # Combine and deduplicate
    all_l1s = []
    seen = set()
    for cap in capabilities + headers:
        cap_clean = cap.strip()
        if cap_clean and cap_clean not in seen and not cap_clean.startswith('Product Epics'):
            seen.add(cap_clean)
            all_l1s.append(cap_clean)

    return all_l1s

def ensure_epics_for_all_l1(epics_md: str, l1_names: List[str]) -> str:
    """
    Ensure that all L1 capabilities have corresponding epics.
    Append placeholder epics for any missing L1s.
    """
    existing_l1s = set(extract_l1_from_epics(epics_md))
    missing_l1s = [name for name in l1_names if name not in existing_l1s]

    if not missing_l1s:
        return epics_md.strip() + "\n"

    # Get next epic ID
    existing_ids = extract_epic_ids(epics_md)
    if existing_ids:
        last_id_num = max([int(eid.split('-')[1]) for eid in existing_ids])
        next_id = last_id_num + 1
    else:
        next_id = 1

    out = epics_md.strip()
    if not out.startswith("# Product Epics"):
        out = "# Product Epics\n\n" + out

    out += "\n\n"

    for l1_name in missing_l1s:
        epic_id = f"EP-{next_id:03d}"
        next_id += 1

        out += f"""## {l1_name}

**Epic ID**: {epic_id}
**Capability**: {l1_name}
**Domain**: (TBD)
**Priority**: P1
**Complexity**: Medium

**Description**
- (TBD - Epic details need to be defined)

**Business Objective**
- (TBD)

**Target Personas**
- Primary: (TBD)
- Secondary: (TBD)

**Success Criteria**
- (TBD)

**Scope (Capabilities)**
- (TBD)

**Related Features**
- (TBD)

**Dependencies**
- None

**Acceptance Criteria**
- [ ] (TBD)

**Out of Scope**
- (TBD)

---

"""

    return out.strip() + "\n"

def validate_epic_structure(epics_md: str) -> Tuple[bool, List[str]]:
    """
    Validate that the epic markdown has the expected structure.
    Returns: (is_valid, list_of_issues)
    """
    issues = []

    # Check for main heading
    if "# Product Epics" not in epics_md:
        issues.append("Missing '# Product Epics' main heading")

    # Check for epic IDs
    epic_ids = extract_epic_ids(epics_md)
    if not epic_ids:
        issues.append("No Epic IDs found")

    # Check for required sections in each epic
    required_sections = [
        "Epic ID",
        "Capability",
        "Domain",
        "Priority",
        "Complexity",
        "Description",
        "Business Objective",
        "Target Personas",
        "Success Criteria",
        "Scope (Capabilities)",
        "Related Features",
        "Dependencies",
        "Acceptance Criteria",
        "Out of Scope"
    ]

    # Count how many epics we have (based on ## headers, excluding main heading)
    epic_headers = re.findall(r'^##\s+(.+)$', epics_md, flags=re.MULTILINE)
    epic_count = len([h for h in epic_headers if h.strip() != "Product Epics"])

    for section in required_sections:
        pattern = rf'\*\*{re.escape(section)}\*\*:'
        matches = re.findall(pattern, epics_md)
        if len(matches) < epic_count:
            issues.append(f"Missing or incomplete '{section}' sections (found {len(matches)}, expected {epic_count})")

    return (len(issues) == 0, issues)

def add_epic_summary_header(epics_md: str) -> str:
    """
    Add a summary section at the top with epic count and overview.
    """
    epic_ids = extract_epic_ids(epics_md)
    epic_count = len(epic_ids)

    # Extract priorities
    priorities = re.findall(r'\*\*Priority\*\*:\s*(P\d)', epics_md)
    p0_count = priorities.count('P0')
    p1_count = priorities.count('P1')
    p2_count = priorities.count('P2')

    summary = f"""# Product Epics

**Total Epics**: {epic_count}
**Priorities**: P0: {p0_count} | P1: {p1_count} | P2: {p2_count}

This document defines high-level epics derived from the capability map. Each epic represents a major body of work that delivers one or more business capabilities.

---

"""

    # Remove the old heading if it exists
    epics_md = re.sub(r'^# Product Epics\s*\n', '', epics_md, flags=re.MULTILINE)

    return summary + epics_md.strip() + "\n"
