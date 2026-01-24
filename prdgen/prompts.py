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

def features_prompt(prd_markdown: str, epics_md: str) -> str:
    return f"""You are a senior Product Manager and Tech Lead creating detailed features from epics.

From the PRD and Epics below, create a structured feature list organized by epic.

For each Epic, generate 3-8 features that deliver the epic's capabilities.

For each feature, include these sections (in this exact order):

**Feature ID**: F-XXX (sequential numbering starting from F-001, global across all epics)
**Epic**: EP-XXX ([Epic Name])
**Feature Name**: [Clear, concise name]

**Description**
[2-3 sentences explaining what this feature does and the value it provides]

**Primary Persona**: [Main user of this feature]
**Secondary Personas**: [Additional users who benefit]
**Priority**: P0/P1/P2 (inherit or refine from epic priority)
**Complexity**: High / Medium / Low

**Acceptance Criteria**
- [ ] [Specific, testable criterion 1]
- [ ] [Specific, testable criterion 2]
- [ ] [Specific, testable criterion 3]
- [ ] [Additional criteria as needed, 3-6 total]

**Dependencies**
[List feature IDs this depends on, or external dependencies. Use "None" if independent]

**Risks**
[List potential risks or challenges in implementing this feature]

Hard rules:
- Organize features by Epic (group under each epic)
- Do NOT invent features beyond what's implied in the PRD and Epic scope
- Each feature must clearly contribute to its parent epic's objectives
- Feature IDs are globally sequential (F-001, F-002, etc.), not per-epic
- Acceptance criteria must be specific, measurable, and testable
- Priority should align with epic priority unless there's a good reason to differ

PRD:
{prd_markdown}

EPICS:
{epics_md}

Return ONLY the feature list in Markdown. Use this structure:

# Product Features

**Total Features**: XX
**By Epic**: EP-001: X features | EP-002: X features | EP-003: X features

---

## Epic EP-001: [Epic Name]

### Feature F-001: [Feature Name]

**Feature ID**: F-001
**Epic**: EP-001 ([Epic Name])
**Feature Name**: [Name]

**Description**
[Description]

**Primary Persona**: [Persona]
**Secondary Personas**: [Personas]
**Priority**: P0
**Complexity**: High

**Acceptance Criteria**
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

**Dependencies**
[Dependencies or "None"]

**Risks**
[Risks]

---

### Feature F-002: [Feature Name]
...
"""

def user_stories_prompt(prd_markdown: str, epics_md: str, features_md: str) -> str:
    return f"""You are a Product Manager and Scrum Master creating detailed user stories for development teams.

From the PRD, Epics, and Features below, generate user stories organized by epic and feature.

For each Feature, create 3-6 user stories that represent specific user-facing scenarios.

For each user story, include these sections (in this exact order):

**Story ID**: US-XXX (sequential numbering starting from US-001, global across all features)
**Feature**: F-XXX ([Feature Name])
**Epic**: EP-XXX ([Epic Name])
**Priority**: P0/P1/P2 (inherit from feature)
**Story Points**: 1/2/3/5/8/13 (Fibonacci scale, estimate based on complexity)
**Persona**: [Specific persona who benefits from this story]

**User Story**
As a [persona],
I want to [action],
So that [benefit].

**Acceptance Criteria**
- [ ] Given [context], When [action], Then [outcome]
- [ ] Given [context], When [action], Then [outcome]
- [ ] Given [context], When [action], Then [outcome]
[3-5 criteria per story, using Gherkin Given/When/Then format]

**Technical Notes**
- [API endpoints, data models, integration points]
- [Any technical considerations for developers]

**Dependencies**
[List story IDs this depends on, or state "None"]

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

Hard rules:
- Organize stories by Epic, then Feature (hierarchical structure)
- Do NOT invent functionality beyond what's in the features
- Story IDs are globally sequential (US-001, US-002, etc.)
- Use standard "As a... I want... So that..." format
- Acceptance criteria MUST use Gherkin Given/When/Then format
- Story points follow Fibonacci: 1, 2, 3, 5, 8, 13
- Estimate story points based on:
  * Complexity (low=1-2, medium=3-5, high=8-13)
  * Number of acceptance criteria
  * Dependencies on other stories
- Each story should be independently deliverable and testable
- Technical notes should guide developers without being too prescriptive

PRD:
{prd_markdown}

EPICS:
{epics_md}

FEATURES:
{features_md}

Return ONLY the user stories in Markdown. Use this structure:

# User Stories

**Total Stories**: XX
**Total Story Points**: XXX
**By Epic**: EP-001: XX stories | EP-002: XX stories

---

## Epic EP-001: [Epic Name]

### Feature F-001: [Feature Name]

#### US-001: [Story Title]

**Story ID**: US-001
**Feature**: F-001 ([Feature Name])
**Epic**: EP-001 ([Epic Name])
**Priority**: P0
**Story Points**: 5
**Persona**: [Persona]

**User Story**
As a [persona],
I want to [action],
So that [benefit].

**Acceptance Criteria**
- [ ] Given [context], When [action], Then [outcome]
- [ ] Given [context], When [action], Then [outcome]
- [ ] Given [context], When [action], Then [outcome]

**Technical Notes**
- [Technical details]

**Dependencies**
- None

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

#### US-002: [Story Title]
...
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

def epics_prompt(prd_markdown: str, capabilities_md: str, cards_md: str) -> str:
    return f"""You are a Product Manager and Technical Architect creating high-level epics for development planning.

From the inputs below, generate a structured list of product epics. Each epic should represent a major body of work that delivers one L1 capability.

For each L1 capability in the capability map, create ONE epic with these sections (in this exact order):

**Epic ID**: EP-XXX (sequential numbering starting from EP-001)
**Capability**: [L1 Capability Name - exact name from capability map]
**Domain**: [L0 Domain Name from capability map]
**Priority**: P0 (must-have) / P1 (should-have) / P2 (nice-to-have) - infer from PRD Goals and requirements
**Complexity**: High / Medium / Low - based on scope and L2 count

**Description**
[2-3 sentences explaining what this epic delivers - use capability card description]

**Business Objective**
[Clear statement of business value - use capability card objective]

**Target Personas**
- Primary: [from capability card]
- Secondary: [from capability card]

**Success Criteria**
[Specific, measurable criteria - use capability card Success Signals]

**Scope (Capabilities)**
[List all L2 sub-capabilities from the capability map that fall under this L1]

**Dependencies**
[List other epics this depends on, or state "None" if independent]

**Acceptance Criteria**
[3-6 specific, testable criteria that define "done"]

**Out of Scope**
[Explicitly state what this epic does NOT include]

Hard rules:
- Create exactly ONE epic per L1 capability
- Use exact L1 capability names from the capability map
- Do NOT invent capabilities not in the inputs
- Infer priority from PRD Goals and Functional Requirements sections
- Keep each epic focused on delivering one L1 capability
- Ensure dependencies reference other epic IDs (EP-XXX format)
- Make acceptance criteria specific and measurable

CAPABILITY MAP:
{capabilities_md}

CAPABILITY CARDS:
{cards_md}

PRD:
{prd_markdown}

Return ONLY the epics in Markdown format. Use this structure:

# Product Epics

## [L1 Capability Name 1]

**Epic ID**: EP-001
...

---

## [L1 Capability Name 2]

**Epic ID**: EP-002
...
"""
