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
