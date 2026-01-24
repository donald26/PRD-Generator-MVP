import re
from typing import List, Dict, Tuple

def extract_feature_ids(features_md: str) -> List[str]:
    """
    Extract all Feature IDs from the generated features markdown.
    Returns: List of feature IDs (e.g., ['F-001', 'F-002'])
    """
    feature_ids = re.findall(r'\*\*Feature ID\*\*:\s*(F-\d+)', features_md)
    return feature_ids

def extract_epic_feature_mapping(features_md: str) -> Dict[str, List[str]]:
    """
    Extract mapping of Epic IDs to their Feature IDs.
    Returns: {epic_id: [feature_ids]}
    """
    mapping = {}
    current_epic = None

    for line in features_md.split('\n'):
        # Look for epic headers: ## Epic EP-001: [Name]
        epic_match = re.match(r'^##\s+Epic\s+(EP-\d+):', line.strip())
        if epic_match:
            current_epic = epic_match.group(1)
            if current_epic not in mapping:
                mapping[current_epic] = []
            continue

        # Look for feature IDs under current epic
        feature_match = re.search(r'\*\*Feature ID\*\*:\s*(F-\d+)', line)
        if feature_match and current_epic:
            feature_id = feature_match.group(1)
            if feature_id not in mapping[current_epic]:
                mapping[current_epic].append(feature_id)

    return mapping

def extract_features_from_epics(epics_md: str) -> List[str]:
    """
    Extract list of epic IDs from epics markdown.
    Returns: List of epic IDs (e.g., ['EP-001', 'EP-002'])
    """
    epic_ids = re.findall(r'\*\*Epic ID\*\*:\s*(EP-\d+)', epics_md)
    return epic_ids

def validate_feature_structure(features_md: str) -> Tuple[bool, List[str]]:
    """
    Validate that features markdown has expected structure.
    Returns: (is_valid, list_of_issues)
    """
    issues = []

    # Check for main heading
    if "# Product Features" not in features_md:
        issues.append("Missing '# Product Features' main heading")

    # Check for feature IDs
    feature_ids = extract_feature_ids(features_md)
    if not feature_ids:
        issues.append("No Feature IDs found")

    # Check for required sections per feature
    required_sections = [
        "Feature ID",
        "Epic",
        "Feature Name",
        "Description",
        "Primary Persona",
        "Priority",
        "Complexity",
        "Acceptance Criteria",
        "Dependencies",
        "Risks"
    ]

    feature_count = len(feature_ids)

    for section in required_sections:
        pattern = rf'\*\*{re.escape(section)}\*\*:'
        matches = re.findall(pattern, features_md)
        if len(matches) < feature_count:
            issues.append(f"Missing or incomplete '{section}' sections (found {len(matches)}, expected {feature_count})")

    # Check for acceptance criteria checkboxes
    ac_checkboxes = re.findall(r'- \[ \]', features_md)
    if len(ac_checkboxes) < feature_count * 3:  # At least 3 per feature
        issues.append(f"Insufficient acceptance criteria checkboxes (found {len(ac_checkboxes)}, expected at least {feature_count * 3})")

    return (len(issues) == 0, issues)

def add_feature_summary_header(features_md: str, epics_md: str) -> str:
    """
    Add a summary section at the top with feature count and epic breakdown.
    """
    feature_ids = extract_feature_ids(features_md)
    feature_count = len(feature_ids)

    # Extract epic-to-feature mapping
    epic_feature_map = extract_epic_feature_mapping(features_md)

    # Build epic breakdown
    epic_breakdown_parts = []
    for epic_id in sorted(epic_feature_map.keys()):
        count = len(epic_feature_map[epic_id])
        epic_breakdown_parts.append(f"{epic_id}: {count} features")

    epic_breakdown = " | ".join(epic_breakdown_parts) if epic_breakdown_parts else "No epics mapped"

    # Extract priorities
    priorities = re.findall(r'\*\*Priority\*\*:\s*(P\d)', features_md)
    p0_count = priorities.count('P0')
    p1_count = priorities.count('P1')
    p2_count = priorities.count('P2')

    summary = f"""# Product Features

**Total Features**: {feature_count}
**By Epic**: {epic_breakdown}
**By Priority**: P0: {p0_count} | P1: {p1_count} | P2: {p2_count}

This document defines detailed features organized by epic. Each feature includes acceptance criteria, personas, dependencies, and risks.

---

"""

    # Remove old heading if it exists
    features_md = re.sub(r'^# Product Features\s*\n', '', features_md, flags=re.MULTILINE)

    # Remove any existing summary block (between heading and first ##)
    features_md = re.sub(
        r'^(# Product Features.*?\n)(.*?)\n(---\s*\n)?(##\s+Epic)',
        r'\4',
        features_md,
        flags=re.DOTALL | re.MULTILINE
    )

    return summary + features_md.strip() + "\n"

def ensure_features_for_epics(features_md: str, epic_ids: List[str]) -> str:
    """
    Ensure all epics have at least a placeholder feature section.
    Append placeholder sections for missing epics.
    """
    epic_feature_map = extract_epic_feature_mapping(features_md)
    existing_epics = set(epic_feature_map.keys())
    missing_epics = [eid for eid in epic_ids if eid not in existing_epics]

    if not missing_epics:
        return features_md.strip() + "\n"

    # Get next feature ID
    existing_ids = extract_feature_ids(features_md)
    if existing_ids:
        last_id_num = max([int(fid.split('-')[1]) for fid in existing_ids])
        next_id = last_id_num + 1
    else:
        next_id = 1

    out = features_md.strip()
    if not out.startswith("# Product Features"):
        out = "# Product Features\n\n" + out

    out += "\n\n"

    for epic_id in missing_epics:
        feature_id = f"F-{next_id:03d}"
        next_id += 1

        out += f"""## Epic {epic_id}: (TBD)

### Feature {feature_id}: (TBD)

**Feature ID**: {feature_id}
**Epic**: {epic_id}
**Feature Name**: (TBD)

**Description**
Feature details need to be defined for this epic.

**Primary Persona**: (TBD)
**Secondary Personas**: (TBD)
**Priority**: P1
**Complexity**: Medium

**Acceptance Criteria**
- [ ] (TBD)

**Dependencies**
None

**Risks**
(TBD)

---

"""

    return out.strip() + "\n"
