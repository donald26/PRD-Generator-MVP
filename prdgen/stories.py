import re
from typing import List, Dict, Tuple

def extract_story_ids(stories_md: str) -> List[str]:
    """
    Extract all User Story IDs from the generated stories markdown.
    Returns: List of story IDs (e.g., ['US-001', 'US-002'])
    """
    story_ids = re.findall(r'\*\*Story ID\*\*:\s*(US-\d+)', stories_md)
    return story_ids

def extract_feature_story_mapping(stories_md: str) -> Dict[str, List[str]]:
    """
    Extract mapping of Feature IDs to their Story IDs.
    Returns: {feature_id: [story_ids]}
    """
    mapping = {}
    current_feature = None

    for line in stories_md.split('\n'):
        # Look for feature headers: ### Feature F-001: [Name]
        feature_match = re.match(r'^###\s+Feature\s+(F-\d+):', line.strip())
        if feature_match:
            current_feature = feature_match.group(1)
            if current_feature not in mapping:
                mapping[current_feature] = []
            continue

        # Look for story IDs under current feature
        story_match = re.search(r'\*\*Story ID\*\*:\s*(US-\d+)', line)
        if story_match and current_feature:
            story_id = story_match.group(1)
            if story_id not in mapping[current_feature]:
                mapping[current_feature].append(story_id)

    return mapping

def extract_epic_story_mapping(stories_md: str) -> Dict[str, List[str]]:
    """
    Extract mapping of Epic IDs to their Story IDs.
    Returns: {epic_id: [story_ids]}
    """
    mapping = {}
    current_epic = None

    for line in stories_md.split('\n'):
        # Look for epic headers: ## Epic EP-001: [Name]
        epic_match = re.match(r'^##\s+Epic\s+(EP-\d+):', line.strip())
        if epic_match:
            current_epic = epic_match.group(1)
            if current_epic not in mapping:
                mapping[current_epic] = []
            continue

        # Look for story IDs under current epic
        story_match = re.search(r'\*\*Story ID\*\*:\s*(US-\d+)', line)
        if story_match and current_epic:
            story_id = story_match.group(1)
            if story_id not in mapping[current_epic]:
                mapping[current_epic].append(story_id)

    return mapping

def validate_story_structure(stories_md: str) -> Tuple[bool, List[str]]:
    """
    Validate that stories markdown has expected structure.
    Returns: (is_valid, list_of_issues)
    """
    issues = []

    # Check for main heading
    if "# User Stories" not in stories_md:
        issues.append("Missing '# User Stories' main heading")

    # Check for story IDs
    story_ids = extract_story_ids(stories_md)
    if not story_ids:
        issues.append("No Story IDs found")

    # Check for required sections per story
    required_sections = [
        "Story ID",
        "Feature",
        "Epic",
        "Priority",
        "Story Points",
        "Persona",
        "User Story",
        "Acceptance Criteria",
        "Dependencies",
        "Definition of Done"
    ]

    story_count = len(story_ids)

    for section in required_sections:
        pattern = rf'\*\*{re.escape(section)}\*\*:'
        matches = re.findall(pattern, stories_md)
        if len(matches) < story_count:
            issues.append(f"Missing or incomplete '{section}' sections (found {len(matches)}, expected {story_count})")

    # Check for "As a" user story format
    as_a_count = len(re.findall(r'As a\s+', stories_md, re.IGNORECASE))
    if as_a_count < story_count:
        issues.append(f"Not all stories follow 'As a...' format (found {as_a_count}, expected {story_count})")

    # Check for Gherkin format (Given/When/Then)
    gherkin_count = len(re.findall(r'Given\s+', stories_md))
    if gherkin_count < story_count:
        issues.append(f"Not all stories have Gherkin acceptance criteria (found {gherkin_count}, expected {story_count})")

    return (len(issues) == 0, issues)

def add_story_summary_header(stories_md: str) -> str:
    """
    Add a summary section at the top with story count and breakdowns.
    """
    story_ids = extract_story_ids(stories_md)
    story_count = len(story_ids)

    # Extract epic-to-story mapping
    epic_story_map = extract_epic_story_mapping(stories_md)

    # Build epic breakdown
    epic_breakdown_parts = []
    for epic_id in sorted(epic_story_map.keys()):
        count = len(epic_story_map[epic_id])
        epic_breakdown_parts.append(f"{epic_id}: {count} stories")

    epic_breakdown = " | ".join(epic_breakdown_parts) if epic_breakdown_parts else "No epics mapped"

    # Extract priorities
    priorities = re.findall(r'\*\*Priority\*\*:\s*(P\d)', stories_md)
    p0_count = priorities.count('P0')
    p1_count = priorities.count('P1')
    p2_count = priorities.count('P2')

    # Extract story points for total estimation
    story_points = re.findall(r'\*\*Story Points\*\*:\s*(\d+)', stories_md)
    total_points = sum([int(sp) for sp in story_points]) if story_points else 0

    summary = f"""# User Stories

**Total Stories**: {story_count}
**Total Story Points**: {total_points}
**By Epic**: {epic_breakdown}
**By Priority**: P0: {p0_count} | P1: {p1_count} | P2: {p2_count}

This document defines user stories organized by epic and feature. Each story includes Gherkin-style acceptance criteria, story point estimates, and implementation notes.

---

"""

    # Remove old heading if it exists
    stories_md = re.sub(r'^# User Stories\s*\n', '', stories_md, flags=re.MULTILINE)

    # Remove any existing summary block
    stories_md = re.sub(
        r'^(# User Stories.*?\n)(.*?)\n(---\s*\n)?(##\s+Epic)',
        r'\4',
        stories_md,
        flags=re.DOTALL | re.MULTILINE
    )

    return summary + stories_md.strip() + "\n"

def estimate_story_points(complexity: str, ac_count: int, has_dependencies: bool) -> int:
    """
    Estimate story points based on complexity, acceptance criteria count, and dependencies.
    Uses Fibonacci sequence: 1, 2, 3, 5, 8, 13
    """
    base_points = {
        "Low": 1,
        "Medium": 3,
        "High": 5
    }

    points = base_points.get(complexity, 3)

    # Adjust for number of acceptance criteria (more criteria = more complexity)
    if ac_count > 5:
        points += 2
    elif ac_count > 3:
        points += 1

    # Adjust for dependencies
    if has_dependencies:
        points += 1

    # Map to Fibonacci
    fibonacci = [1, 2, 3, 5, 8, 13]
    for fib in fibonacci:
        if points <= fib:
            return fib

    return 13  # Maximum

def format_gherkin_criteria(criteria_list: List[str]) -> str:
    """
    Format acceptance criteria in Gherkin (Given/When/Then) format.
    """
    gherkin_lines = []
    for criterion in criteria_list:
        # If not already in Gherkin format, convert it
        if not any(keyword in criterion for keyword in ["Given", "When", "Then"]):
            gherkin_lines.append(f"- [ ] Given [context], When [action], Then {criterion}")
        else:
            gherkin_lines.append(f"- [ ] {criterion}")

    return "\n".join(gherkin_lines)

def ensure_stories_for_features(stories_md: str, feature_ids: List[str]) -> str:
    """
    Ensure all features have at least one placeholder story.
    Append placeholder sections for missing features.
    """
    feature_story_map = extract_feature_story_mapping(stories_md)
    existing_features = set(feature_story_map.keys())
    missing_features = [fid for fid in feature_ids if fid not in existing_features]

    if not missing_features:
        return stories_md.strip() + "\n"

    # Get next story ID
    existing_ids = extract_story_ids(stories_md)
    if existing_ids:
        last_id_num = max([int(sid.split('-')[1]) for sid in existing_ids])
        next_id = last_id_num + 1
    else:
        next_id = 1

    out = stories_md.strip()
    if not out.startswith("# User Stories"):
        out = "# User Stories\n\n" + out

    out += "\n\n"

    for feature_id in missing_features:
        story_id = f"US-{next_id:03d}"
        next_id += 1

        out += f"""### Feature {feature_id}: (TBD)

#### {story_id}: (TBD)

**Story ID**: {story_id}
**Feature**: {feature_id}
**Epic**: (TBD)
**Priority**: P1
**Story Points**: 3
**Persona**: (TBD)

**User Story**
As a (persona),
I want to (action),
So that (benefit).

**Acceptance Criteria**
- [ ] Given (context), When (action), Then (outcome)

**Technical Notes**
- (TBD)

**Dependencies**
- None

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing
- [ ] Documentation updated

---

"""

    return out.strip() + "\n"
