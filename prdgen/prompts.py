PRD_OUTLINE = [
    "Overview",
    "Problem Statement",
    "Goals",
    "Non-Goals",
    "Target Personas",
    "User Journeys",
    "Functional Requirements",
    "Non-Functional Requirements",
    "Success Metrics",
    "Assumptions & Open Questions",
    "Out of Scope",
]

def corpus_summarize_prompt(corpus: str) -> str:
    return f"""You are a Staff Product Manager. You are given multiple documents (meeting notes, docs, emails, etc.) about a product idea.

Task:
- Extract the most important facts and constraints WITHOUT inventing anything.
- Produce:
  1) A short 'Product Intent' paragraph (3-6 sentences)
  2) Key facts (bullets)
  3) Constraints / requirements (bullets)
  4) Open questions (bullets)
  5) Glossary (optional)

Hard rules:
- If the documents conflict, call it out under Open Questions.
- Keep the summary concise (<= 500 words).

DOCUMENTS:
{corpus}

Return ONLY the summary in Markdown with these headings:
## Product Intent
## Key Facts
## Constraints
## Open Questions
## Glossary
"""

def prd_prompt(product_info_md: str) -> str:
    outline = "\n".join([f"## {h}" for h in PRD_OUTLINE])
    return f"""You are a senior Product Manager writing a PRD.

Write a detailed PRD in Markdown based on the product information below.
Hard rules:
- Use the exact section headings in this outline (keep order).
- Be concrete and implementation-oriented, but do not write code.
- If information is missing, put it under 'Assumptions & Open Questions' instead of guessing.
- Keep it to ~2–4 pages of Markdown (not a novel).

PRD OUTLINE:
{outline}

PRODUCT INFORMATION:
{product_info_md}

Return ONLY the PRD Markdown.
"""

def capabilities_prompt(prd_markdown: str) -> str:
    return f"""You are a Product Architect. From the PRD below, produce a hierarchical capability map.

Output a capability hierarchy with:
- L0 (Domains) : 4–8 items
- L1 (Capabilities) under each L0 : 3–8 items
- L2 (Sub-capabilities) under each L1 : 2–6 items

Hard rules:
- Capabilities must be phrased as stable business abilities (not UI screens).
- Do NOT invent capabilities not implied by the PRD.
- Keep it readable in Markdown.

PRD:
{prd_markdown}

Return ONLY the capability hierarchy in Markdown using:
# L0: <name>
## L1: <name>
- L2: <name>
"""

def capability_cards_prompt(prd_markdown: str, capabilities_md: str, l1_names: list) -> str:
    l1_list = "\n".join([f"- {n}" for n in l1_names])
    return f"""You are a Product Architect. Create a clean set of L1 Capability Cards.

You are given:
1) a PRD
2) a capability hierarchy (L0/L1/L2)
3) the exact list of L1 capability names

You MUST produce exactly ONE card per L1 capability name, using the exact name text.

For each L1 capability card include these sections (keep them in this order):
**Description**
**Objective**
**Primary Personas**
**Secondary Personas**
**Design Considerations**
**Success Signals**
**Related L2 (from capability map)**

Style rules:
- Use Markdown.
- Keep each section concise (1–5 bullets).
- Design considerations should include product + system-level constraints/tradeoffs (scale, privacy, usability, reliability), not UI mockups.

L1 CAPABILITIES (EXACT NAMES):
{l1_list}

CAPABILITY MAP:
{capabilities_md}

PRD:
{prd_markdown}

Return ONLY the capability cards Markdown, with this structure:

## <L1 Capability Name>
**Description**
- ...
...
"""

def features_prompt(prd_markdown: str) -> str:
    return f"""You are a senior Product Manager and Tech Lead collaborating.

From the PRD below, create a structured feature list in Markdown.

Hard rules:
- Do NOT invent features not implied by the PRD.
- Group features into 4–8 logical groups.
- For each feature include:
  - Description (1–2 lines)
  - Primary Persona
  - Priority (P0/P1/P2)
  - Dependencies (0+)
  - Risks (0+)
- Keep the output concise but complete.

PRD:
{prd_markdown}

Return ONLY the feature list Markdown.
"""

def lean_canvas_prompt(prd_markdown: str, capabilities_md: str) -> str:
    return f"""You are a startup advisor and product strategist.

Create a Lean Canvas (1-page) from the PRD and capability map below.
Use exactly these sections:

## Problem
## Customer Segments
## Unique Value Proposition
## Solution
## Channels
## Revenue Streams
## Cost Structure
## Key Metrics
## Unfair Advantage
## Existing Alternatives

Hard rules:
- Keep each section to 3–6 bullets max.
- Do NOT invent numbers; if unknown, phrase as assumptions.
- Align the 'Solution' with the capability map.

PRD:
{prd_markdown}

CAPABILITIES:
{capabilities_md}

Return ONLY the Lean Canvas in Markdown.
"""
