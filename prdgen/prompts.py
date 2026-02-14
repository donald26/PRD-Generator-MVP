from .prompt_templates import get_template_structure

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

def context_assessment_prompt(corpus: str) -> str:
    """
    NEW: First-stage document context assessment prompt.
    Extracts structured information from input documents before any artifact generation.
    """
    return f"""You are a Senior Product Analyst conducting a comprehensive document context assessment.

Your task is to analyze the provided documents and extract a structured summary of the product context.

**CRITICAL RULES:**
- Extract ONLY information explicitly stated or clearly implied in the documents
- Do NOT invent, assume, or hallucinate missing information
- If information is missing for a section, state "Not specified in documents"
- If documents conflict, note the conflict explicitly
- For source traceability, reference the file names where information was found

**OUTPUT FORMAT:**
Produce a structured assessment with these EXACT sections (in this order):

## Problem / Opportunity
[Describe the core problem(s) or business opportunity the documents address. 2-4 sentences.]

## Goals
[List explicit objectives mentioned in the documents]
- Goal 1
- Goal 2
- ...

## Non-Goals
[List explicit exclusions or out-of-scope items mentioned]
- Non-goal 1
- Non-goal 2
- ...
[If none specified, state: "Not explicitly defined in documents"]

## Target Personas / Users
[List user types, personas, or stakeholders mentioned]
- Persona 1: [Brief description]
- Persona 2: [Brief description]
- ...

## Key Functional Requirements
[High-level capabilities the product must provide - NOT user stories, just capabilities]
- Requirement 1
- Requirement 2
- ...

## Constraints & Assumptions
**Technical Constraints:**
- [List technical constraints if mentioned]

**Business Constraints:**
- [List business constraints if mentioned]

**Assumptions:**
- [List key assumptions made in the documents]

[If none for a category, state: "None specified"]

## Risks, Gaps, and Open Questions
**Risks:**
- [Potential risks mentioned or implied]

**Information Gaps:**
- [Missing information that should be clarified]

**Open Questions:**
- [Unresolved questions or ambiguities in the documents]

**Conflicts:**
- [Any contradictory information between documents]

## Source Traceability
[For each major section above, indicate which input file(s) contributed information]

**Problem/Opportunity:** [file1.docx, file2.md]
**Goals:** [file1.docx]
**Personas:** [file3.txt]
**Requirements:** [file1.docx, file4.md]
**Constraints:** [file2.md]
[etc.]

---

DOCUMENTS:
{corpus}

Return ONLY the structured assessment in Markdown format using the sections above.
"""

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
    # Get feature template structure
    template_structure = get_template_structure("feature")

    return f"""You are a senior Product Manager and Tech Lead creating detailed features from epics.

From the PRD and Epics below, create a structured feature list organized by epic.

IMPORTANT: Follow the Feature Template structure provided below.

{template_structure}

Guidelines:
- Feature Name: Clear, user-centric name
- Feature Description: What the feature does and why it exists
- Associated Epic: Link to parent epic (EP-XXX)
- User Value Statement: "This feature enables <persona> to <action> so that <outcome>"
- Functional Requirements: Deterministic, testable behaviors (3-6 items)
- Non-Functional Requirements: Latency, throughput, security, auditability
- User Interaction/Flow: High-level user or system flow
- Edge Cases & Exceptions: Failure scenarios and retries
- Dependencies: APIs, data sources, third-party systems (use "None" if independent)
- Acceptance Criteria: Feature-level Definition of Done (specific, testable)
- Telemetry & Observability: Logs, metrics, and alerts

Hard rules:
- Generate 3-8 features per epic that deliver the epic's capabilities
- Do NOT invent features beyond what's implied in the PRD and Epic scope
- Each feature must clearly contribute to its parent epic's objectives
- Feature IDs are globally sequential (F-001, F-002, etc.), not per-epic
- All requirements must be deterministic and testable
- Base functional requirements strictly on PRD and epic scope

INPUT DOCUMENTS:

PRD:
{prd_markdown}

EPICS:
{epics_md}

Return ONLY the feature list in Markdown following the template structure.
Organize features by Epic. Each feature should be a complete, self-contained section.

Use this format:

# Product Features

**Total Features**: XX
**By Epic**: EP-001: X features | EP-002: X features

---

## Epic EP-001: [Epic Name]

### Feature F-001: [Feature Name]

[Follow template structure for each feature]

---

### Feature F-002: [Feature Name]
...
"""

def user_stories_prompt(prd_markdown: str, epics_md: str, features_md: str) -> str:
    # Get user story template structure
    template_structure = get_template_structure("user_story")

    return f"""You are a Product Manager and Scrum Master creating detailed user stories for development teams.

From the PRD, Epics, and Features below, generate user stories organized by epic and feature.

IMPORTANT: Follow the User Story Template structure provided below.

{template_structure}

Guidelines:
- Story ID: US-XXX (sequential numbering starting from US-001, global across all features)
- Title: Action-oriented and specific
- As a: Specific persona from the feature
- I want to: Specific action or capability
- So that: Clear value or outcome
- Detailed Description: Clarifies intent without unnecessary solution bias
- Acceptance Criteria: Use Gherkin format - Given <context>, When <action>, Then <expected outcome> (3-5 criteria per story)
- Functional Notes: API behavior, validation rules, data transformations
- Non-Functional Requirements: Performance, security, compliance constraints
- Dependencies: List story IDs, features, or external systems this depends on (use "None" if independent)
- Definition of Done: Code complete, tests written, documentation updated, telemetry enabled
- Story Points/Complexity: Use Fibonacci scale (1, 2, 3, 5, 8, 13) based on:
  * Complexity (low=1-2, medium=3-5, high=8-13)
  * Number of acceptance criteria
  * Dependencies on other stories

Hard rules:
- Create 3-6 user stories per feature that represent specific user-facing scenarios
- Do NOT invent functionality beyond what's defined in the features
- Story IDs are globally sequential (US-001, US-002, etc.)
- Use standard "As a... I want... So that..." format
- Acceptance criteria MUST use Gherkin Given/When/Then format
- Each story should be independently deliverable and testable
- Technical notes should guide developers without being too prescriptive
- Base all content strictly on provided PRD, epics, and features

INPUT DOCUMENTS:

PRD:
{prd_markdown}

EPICS:
{epics_md}

FEATURES:
{features_md}

Return ONLY the user stories in Markdown following the template structure.
Organize stories by Epic, then Feature (hierarchical structure).
Each story should be a complete, self-contained section.

Use this format:

# User Stories

**Total Stories**: XX
**Total Story Points**: XXX
**By Epic**: EP-001: XX stories | EP-002: XX stories

---

## Epic EP-001: [Epic Name]

### Feature F-001: [Feature Name]

#### US-001: [Story Title]

[Follow template structure for each story]

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
    # Get epic template structure
    template_structure = get_template_structure("epic")

    return f"""You are a Product Manager and Technical Architect creating high-level epics for development planning.

From the inputs below, generate a structured list of product epics. Each epic should represent a major body of work that delivers one L1 capability.

IMPORTANT: Follow the Epic Template structure provided below.

{template_structure}

Guidelines:
- Create exactly ONE epic per L1 capability from the capability map
- Use exact L1 capability names from the capability map
- Epic Name should be outcome-oriented (verb + object)
- Epic Summary should describe the business problem and intended outcome (1-2 paragraphs)
- Business Objective should state measurable business outcomes
- In Scope: Included workflows and capabilities from the capability map
- Out of Scope: Explicit exclusions
- Primary Personas: Use personas from capability cards
- Success Metrics/KPIs: Adoption, efficiency, revenue/risk/quality signals from capability cards
- Key Capabilities Enabled: Reference L2/L3 capabilities from the capability map
- Dependencies: Platform, data, external teams, regulatory (use "None" if independent)
- Non-Functional Requirements: Performance, security, availability, compliance
- Assumptions & Constraints: Known assumptions and constraints from PRD
- Risks & Mitigations: Identified risks and mitigation strategies

Hard rules:
- Do NOT invent capabilities not in the inputs
- Infer priority from PRD Goals and Functional Requirements sections
- Make metrics and success criteria specific and measurable
- Base all content on provided PRD, capability map, and capability cards

INPUT DOCUMENTS:

CAPABILITY MAP:
{capabilities_md}

CAPABILITY CARDS:
{cards_md}

PRD:
{prd_markdown}

Return ONLY the epics in Markdown format following the template structure.
Each epic should be a complete, self-contained section.
"""


def architecture_prompt(prd_markdown: str, capabilities_md: str, context_summary_md: str = "") -> str:
    """
    Generate prompt for technical architecture reference diagram.

    Args:
        prd_markdown: Generated PRD content
        capabilities_md: Generated capability map
        context_summary_md: Optional context summary for additional grounding

    Returns:
        Formatted prompt string for architecture generation
    """
    context_section = ""
    if context_summary_md:
        context_section = f"""
CONTEXT SUMMARY (for additional grounding):
{context_summary_md}

---
"""

    return f"""You are a Solutions Architect creating a Technical Architecture Reference Diagram.

Your task is to derive a system architecture from the PRD and Capability Map provided.

**CRITICAL RULES:**
- Extract architecture ONLY from explicitly stated or clearly implied requirements
- Do NOT invent components, services, databases, or technologies not in the inputs
- If information is missing for a component detail, explicitly state "Not specified"
- Include AI/ML components ONLY if RAG, LLM, ML models, or vector databases are mentioned
- Flag all assumptions and unresolved questions

**COMPONENT TYPES** (use only these):
- client: User-facing applications (web, mobile, CLI)
- gateway: API gateways, load balancers, reverse proxies
- service: Backend services, microservices, APIs
- worker: Background processors, job runners, async handlers
- database: Relational/document databases
- cache: In-memory caches (Redis, Memcached)
- queue: Message queues (RabbitMQ, SQS, Kafka topics)
- stream: Event streams, Kafka, Kinesis
- ml_model: ML model serving endpoints
- vector_db: Vector databases for RAG/embeddings
- idp: Identity providers, auth services
- observability: Logging, monitoring, tracing systems
- external_system: Third-party integrations

**OUTPUT FORMAT:**
Produce a structured document with these EXACT sections:

## Title
[Product Name] Technical Architecture

## Overview
[2-4 sentences describing the system architecture purpose and scope]

## Assumptions
- [List assumptions made to fill gaps]

## Open Questions
- [List unresolved questions that need clarification]

## Components

### [Component Name]
- **ID:** [unique_lowercase_id using underscores]
- **Type:** [component_type from list above]
- **Responsibilities:**
  - [Responsibility 1]
  - [Responsibility 2]
- **Data Stores:** [list or "None"]
- **Security Notes:** [list or "Not specified"]

[Repeat for each component]

## Data Flows

### [Flow Description]
- **From:** [source_component_id]
- **To:** [target_component_id]
- **Description:** [what data/request flows]
- **Protocol:** [HTTP/gRPC/WebSocket/AMQP/etc.]
- **Auth:** [OAuth2/JWT/API Key/mTLS/None]
- **Data:** [list of data types transferred]

[Repeat for each significant flow]

## Non-Functional Requirements

### Availability
[State availability requirements or "Not specified"]

### Performance
[State performance requirements or "Not specified"]

### Security
[State security requirements or "Not specified"]

### Compliance
[State compliance requirements or "Not specified"]

### Observability
[State observability requirements or "Not specified"]

## Deployment View

### Environment
[Cloud provider, on-prem, hybrid, or "Not specified"]

### Scaling Notes
- [Scaling consideration 1]
- [Scaling consideration 2]

### Multi-Tenancy
[Multi-tenancy approach or "Not specified"]

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        [client components]
    end

    subgraph Platform["Core Platform"]
        [service components]
    end

    subgraph Data["Data Layer"]
        [database/cache components]
    end

    subgraph AI["AI Layer"]
        [ml/vector components - ONLY if applicable]
    end

    subgraph External["External Integrations"]
        [external system components]
    end

    [data flow arrows between components]
```

---

{context_section}PRD:
{prd_markdown}

---

CAPABILITY MAP:
{capabilities_md}

---

Return ONLY the architecture document in Markdown format using the sections above.
Ensure the Mermaid diagram is syntactically correct and includes all defined components.
"""


def architecture_options_prompt(
    prd_markdown: str,
    capabilities_md: str,
    base_architecture_md: str,
    context_summary_md: str = ""
) -> str:
    """
    Generate prompt for architecture options per capability.

    Args:
        prd_markdown: Generated PRD content
        capabilities_md: Generated capability map
        base_architecture_md: The primary architecture reference already generated
        context_summary_md: Optional context summary for additional grounding

    Returns:
        Formatted prompt string for architecture options generation
    """
    context_section = ""
    if context_summary_md:
        context_section = f"""
CONTEXT SUMMARY:
{context_summary_md}

---
"""

    return f"""You are generating alternative architecture patterns for key capabilities.

**TASK:**
Review the base architecture and identify 2-3 capabilities that could benefit from alternative implementation patterns. For each capability, provide 1-2 alternative architecture options with explicit trade-offs.

**SELECTION CRITERIA:**
Only create options for capabilities where:
- Multiple valid architectural patterns exist (e.g., sync vs async, centralized vs distributed)
- The choice materially affects system design, scalability, or operations
- Trade-offs are meaningful and decision-worthy

Do NOT create options for:
- Standard CRUD operations with no meaningful alternatives
- Capabilities with a single obvious implementation
- Areas where the PRD/requirements clearly dictate the approach

**OUTPUT FORMAT:**
For each capability with options, use this EXACT structure:

### [Capability Name]

#### Option 1: [Pattern Label]

**Description:** [2-3 sentences describing this architectural approach]

**Assumptions:**
- [Assumption 1]
- [Assumption 2]

**Trade-offs:**
| Pros | Cons |
|------|------|
| [Pro 1] | [Con 1] |
| [Pro 2] | [Con 2] |

**When to Choose:** [Non-prescriptive guidance on when this pattern fits]

```mermaid
flowchart TB
    [focused diagram showing this pattern]
```

#### Option 2: [Alternative Pattern Label]
[Same structure as Option 1]

---

**IMPORTANT CONSTRAINTS:**
- Keep diagrams focused on the specific capability (not the full system)
- Use logical pattern names, not vendor-specific services
- Each option must have BOTH pros AND cons
- Frame "When to Choose" as conditions, not recommendations
- If insufficient info to define options, note as "Open Question" and skip

---

{context_section}BASE ARCHITECTURE:
{base_architecture_md}

---

PRD:
{prd_markdown}

---

CAPABILITY MAP:
{capabilities_md}

---

Return ONLY the architecture options in Markdown format.
Include 2-3 capabilities with 1-2 options each.
If no capabilities warrant options, return a brief explanation why.
"""


# ---------------------------------------------------------------------------
# Modernization-specific prompts
# ---------------------------------------------------------------------------

def capabilities_modernization_prompt(
    prd_markdown: str,
    context_summary_md: str,
    intake_context_md: str,
) -> str:
    """
    Modernization-path capabilities prompt.
    Uses the Capability_Assessment_Template.md structure.
    Produces: Pillar Overview + Detailed Assessment Tables + Gap Summary.
    """
    template_structure = get_template_structure("capability_assessment")

    return f"""You are a Transformation Architect conducting a capability assessment
for a system modernization initiative.

Your task is to produce a complete Capability Assessment Framework following the
template structure below.

IMPORTANT: Follow the template structure provided.

{template_structure}

Guidelines for Transformation Pillars:
- Derive 3-6 pillars from the DOMAIN described in the documents
- Each pillar needs a mission statement (1-2 sentences)
- Pillars should cover: business process, technology/platform, data, people/org,
  and customer experience dimensions AS RELEVANT to the domain
- Do NOT use the generic pillar names from any reference -- derive from context

Guidelines for Maturity Assessment:
- Use ONLY these four levels: Non-Existent, Lagging, On Par, Leading
- Current State: base on pain points, constraints, current-system descriptions
- Maturity (Current): rate based on explicit evidence in the documents
- Maturity (Target): derive from stated goals and desired outcomes
- Desired Future State: derive from vision, goals, and outcome statements
- If evidence is insufficient, mark as "Unknown" and note in Gap Summary

Guidelines for Gap Summary:
- Group gaps by severity: Critical (Non-Existent->Leading), Major (Lagging->Leading),
  Incremental (On Par->Leading)
- Each gap should be a single actionable line

INPUT DOCUMENTS:

INTAKE CONTEXT (Modernization Questionnaire):
{intake_context_md}

CONTEXT SUMMARY:
{context_summary_md}

PRD:
{prd_markdown}

Return ONLY the Capability Assessment Framework in Markdown following the template.
"""


def capability_cards_modernization_prompt(
    prd_markdown: str,
    capabilities_md: str,
    l1_names: list,
    intake_context_md: str,
) -> str:
    """
    Modernization-path capability cards with migration-specific sections.
    Uses Capability_Card_Modernization_Template.md structure.
    """
    template_structure = get_template_structure("capability_card_modernization")
    l1_list = "\n".join([f"- {n}" for n in l1_names])

    return f"""You are a Transformation Architect creating modernization capability cards.

You MUST produce exactly ONE card per L1 capability listed below.

IMPORTANT: Follow the Modernization Capability Card Template provided.

{template_structure}

Guidelines:
- Current State Assessment: summarise from the capability assessment tables
- Migration Approach: recommend based on the capability's current maturity,
  complexity, and dependencies. Use standard patterns (strangler-fig, big-bang,
  parallel-run, phased cutover).
- Quick Wins: improvements achievable in 0-3 months with minimal risk
- Long-term Investments: changes requiring 3-12+ months of sustained effort
- Legacy Dependencies: specific systems/components that must be decommissioned
  and the trigger condition for decommission
- Transition Risks: be specific, include impact level (H/M/L) and mitigation

L1 CAPABILITIES (EXACT NAMES):
{l1_list}

INTAKE CONTEXT:
{intake_context_md}

CAPABILITY ASSESSMENT:
{capabilities_md}

PRD:
{prd_markdown}

Return ONLY the capability cards in Markdown following the template structure.
"""


# ---------------------------------------------------------------------------
# Roadmap prompts
# ---------------------------------------------------------------------------

def roadmap_prompt(prd_markdown: str, epics_md: str, features_md: str) -> str:
    """Generate a delivery roadmap from PRD, epics, and features."""
    return f"""You are a Product Strategist and Delivery Lead creating a delivery roadmap.

From the PRD, Epics, and Features below, produce a phased delivery roadmap.

Output format:

## Delivery Roadmap

### Release Strategy
[1-2 paragraphs on overall approach]

### Phase MVP (Must-Have)
**Scope:** [1-2 sentences]
**Epics Included:**
- EP-XXX: [Epic Name] - [rationale for MVP inclusion]

**Key Features:**
- F-XXX: [Feature Name]

**Success Criteria:** [measurable criteria for MVP sign-off]

### Phase 1: [Theme Name]
[Same structure as MVP]

### Phase 2: [Theme Name]
[Same structure]

### Phase 3+: [Future / Backlog]
[Items deferred with rationale]

### Dependency Map
| Epic | Depends On | Blocking | Critical Path |
|------|-----------|----------|---------------|
| EP-XXX | EP-YYY | EP-ZZZ | Yes/No |

### Risk-Adjusted Considerations
- [Risk 1]: [impact on timeline]
- [Risk 2]: [impact on timeline]

Hard rules:
- Every epic must appear in exactly one phase
- MVP should be the minimal set that delivers core value
- Dependencies must be respected in phase ordering
- Do NOT invent timelines or team sizes not in the inputs
- If timeline info is missing, use relative sequencing only

INPUT DOCUMENTS:

PRD:
{prd_markdown}

EPICS:
{epics_md}

FEATURES:
{features_md}

Return ONLY the roadmap in Markdown.
"""


def roadmap_modernization_prompt(
    prd_markdown: str,
    epics_md: str,
    features_md: str,
    intake_context_md: str,
) -> str:
    """Modernization roadmap variant with migration wave sequencing."""
    return f"""You are a Transformation Lead creating a modernization delivery roadmap.

From the PRD, Epics, Features, and Modernization Context below, produce a phased
migration roadmap.

Output format:

## Modernization Delivery Roadmap

### Migration Strategy Overview
[1-2 paragraphs on overall migration approach]

### Wave 1: Foundation & Quick Wins
**Scope:** [1-2 sentences]
**Epics Included:**
- EP-XXX: [Epic Name] - [rationale]

**Migration Pattern:** [strangler-fig / parallel-run / phased cutover]
**Legacy Systems Affected:** [list]
**Success Criteria:** [measurable criteria]

### Wave 2: Core Modernization
[Same structure]

### Wave 3: Advanced Capabilities
[Same structure]

### Wave 4+: Optimization & Decommission
[Items deferred with rationale]

### Legacy Decommission Milestones
| Legacy System | Decommission Trigger | Target Wave | Risk |
|---------------|---------------------|-------------|------|
| [system] | [condition] | Wave N | H/M/L |

### Cutover Gates
| Gate | Criteria | Go/No-Go Decision Point |
|------|----------|------------------------|
| [gate name] | [criteria] | [when] |

### Dependency Map
| Epic | Depends On | Blocking | Critical Path |
|------|-----------|----------|---------------|
| EP-XXX | EP-YYY | EP-ZZZ | Yes/No |

### Risk-Adjusted Considerations
- [Risk 1]: [impact on migration timeline]
- [Risk 2]: [impact on migration timeline]

Hard rules:
- Every epic must appear in exactly one wave
- Wave 1 should prioritize quick wins and foundation work
- Dependencies must be respected in wave ordering
- Include legacy decommission milestones
- Include cutover gates for parallel-run scenarios
- Do NOT invent timelines or team sizes not in the inputs

INPUT DOCUMENTS:

PRD:
{prd_markdown}

EPICS:
{epics_md}

FEATURES:
{features_md}

MODERNIZATION CONTEXT:
{intake_context_md}

Return ONLY the roadmap in Markdown.
"""
