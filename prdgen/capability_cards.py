import re
from typing import List

def extract_l1_names(capabilities_md: str) -> List[str]:
    """Extract L1 names from capabilities markdown (## L1: <name>)."""
    names = re.findall(r"^##\s*L1:\s*(.+)$", capabilities_md, flags=re.MULTILINE)
    seen = set()
    out: List[str] = []
    for n in [x.strip() for x in names]:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out

def ensure_cards_for_l1(cards_md: str, l1_names: List[str]) -> str:
    """Append TBD cards for any L1 names missing from the generated cards."""
    existing = set(re.findall(r"^##\s+(.+)$", cards_md, flags=re.MULTILINE))
    missing = [n for n in l1_names if n not in existing]
    if not missing:
        return cards_md.strip() + "\n"
    out = cards_md.strip() + "\n\n"
    for n in missing:
        out += (
            f"## {n}\n\n"
            "**Description**\n- (TBD)\n\n"
            "**Objective**\n- (TBD)\n\n"
            "**Primary Personas**\n- (TBD)\n\n"
            "**Secondary Personas**\n- (TBD)\n\n"
            "**Design Considerations**\n- (TBD)\n\n"
            "**Related L2 (from capability map)**\n- (TBD)\n\n"
        )
    return out.strip() + "\n"


# ---------------------------------------------------------------------------
# Modernization-specific functions
# ---------------------------------------------------------------------------

def extract_l1_names_modernization(capabilities_md: str) -> List[str]:
    """Extract L1 names from modernization capability assessment.

    The modernization format uses Part 2 headers like:
        ### [Pillar Name]: [L1 Capability Name]
    """
    # Match "### Pillar: L1 Name" headers from Part 2
    names = re.findall(
        r"^###\s+.+?:\s+(.+)$", capabilities_md, flags=re.MULTILINE
    )
    seen = set()
    out: List[str] = []
    for n in [x.strip() for x in names]:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def ensure_modernization_cards(cards_md: str, l1_names: List[str]) -> str:
    """Validate modernization cards have migration sections, add TBD if missing."""
    existing = set(re.findall(r"^##\s+(.+)$", cards_md, flags=re.MULTILINE))
    missing = [n for n in l1_names if n not in existing]
    if not missing:
        # Still validate that existing cards have migration sections
        return _ensure_migration_sections(cards_md)
    out = cards_md.strip() + "\n\n"
    for n in missing:
        out += (
            f"## {n}\n\n"
            "**Description**\n- (TBD)\n\n"
            "**Objective**\n- (TBD)\n\n"
            "**Primary Personas**\n- (TBD)\n\n"
            "**Secondary Personas**\n- (TBD)\n\n"
            "**Current State Assessment**\n- (TBD)\n\n"
            "**Design Considerations**\n- (TBD)\n\n"
            "**Success Signals**\n- (TBD)\n\n"
            "**Migration Approach**\n- Recommended pattern: (TBD)\n\n"
            "**Quick Wins** (achievable in 0-3 months)\n- (TBD)\n\n"
            "**Long-term Investments** (3-12+ months)\n- (TBD)\n\n"
            "**Legacy Dependencies to Decommission**\n- (TBD)\n\n"
            "**Transition Risks & Mitigations**\n"
            "| Risk | Impact | Mitigation |\n"
            "|------|--------|------------|\n"
            "| (TBD) | (TBD) | (TBD) |\n\n"
            "**Related L2 (from capability map)**\n- (TBD)\n\n"
        )
    return _ensure_migration_sections(out.strip() + "\n")


def _ensure_migration_sections(cards_md: str) -> str:
    """Check that cards contain key migration sections; warn if missing."""
    required_sections = [
        "Migration Approach",
        "Quick Wins",
        "Transition Risks",
    ]
    for section in required_sections:
        if section.lower() not in cards_md.lower():
            # Add a note at the end rather than modifying card content
            cards_md = cards_md.strip() + (
                f"\n\n> **Warning:** '{section}' section not found in one or more cards. "
                f"Review and add manually.\n"
            )
    return cards_md.strip() + "\n"
