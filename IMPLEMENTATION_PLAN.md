# Implementation Plan: Phased PRD Generation with HITL Gates

## Current Architecture Summary

```
prdgen/                          # Core generation library
  generator.py                   # ArtifactGenerator with 10 generate_* methods
  artifact_types.py              # ArtifactType enum + predefined sets
  dependencies.py                # Dependency resolver + ArtifactCache
  config.py                      # GenerationConfig dataclass
  prompts.py                     # All LLM prompt functions
  prompt_templates.py            # System prompts + template loading
  capability_cards.py            # L1 extraction + card validation
  model.py / ingest.py / cli.py  # Model loading, doc ingestion, CLI

backend/app/
  main.py                        # FastAPI endpoints (job-based, async)
  job_tracker.py                 # JSON-file job persistence
  services/prd_service.py        # Service wrapper around prdgen

templates/
  Epic_Template.md               # Template loaded by prompt_templates.py
  Feature_Template.md            # Template loaded by prompt_templates.py
  User_Story_Template.md         # Template loaded by prompt_templates.py
  Architecture_Template.md       # Template loaded by prompt_templates.py
  capmap.pdf                     # Reference: modernization capability framework

questionnaire/
  greenfield.json                # 16 questions, 5 sections, with mapping fields
  modernization.json             # 18 questions, 7 sections, with mapping fields
```

**Key insight:** The existing `ArtifactGenerator.generate_selected()` already
resolves dependencies and generates artifacts in topological order. The phased
system layers ON TOP of this -- it partitions the artifact set into 3 stages,
pausing between each for human review.

---

## Design Decisions (from capmap.pdf review)

### What the capmap.pdf reveals

The PDF defines a **modernization-specific capability assessment framework** that
is structurally different from the current greenfield hierarchy:

| Dimension | Current Generator (Greenfield) | capmap.pdf (Modernization) |
|---|---|---|
| Top level | `# L0: Domain` (flat label) | **Transformation Pillars** with mission statements |
| Per-capability detail | Just the name in hierarchy | Current State + Maturity level + Desired Future State |
| Maturity model | None | 4-level: Non-Existent / Lagging / On Par / Leading (current + target) |
| Output format | Simple markdown hierarchy | Framework overview + detailed assessment tables per L1 |
| Gap analysis | None | Implicit from current-to-desired maturity delta |

### Decisions made

1. **Single enriched artifact** -- Modernization produces ONE CAPABILITIES artifact
   containing both the framework overview (pillars → L1 → L2) AND the detailed
   assessment tables (current state, maturity, future state). No new artifact type.

2. **LLM-derived pillars** -- The LLM analyzes input docs and derives
   domain-appropriate transformation pillars with mission statements. Not fixed.

3. **Hybrid maturity data** -- LLM drafts current-state descriptions and maturity
   ratings from the input docs + questionnaire answers. At the Phase 1 HITL gate,
   the user can edit/override individual ratings before approving.

4. **Migration-enriched capability cards** -- When `flow_type=modernization`,
   capability cards include additional sections: Migration Approach, Quick Wins,
   Legacy Dependencies, Transition Risks.

---

## Phase-to-Artifact Mapping

| Phase | User-facing Label | Artifacts Generated |
|-------|-------------------|---------------------|
| **1** | Context Summary + PRD + Capabilities | `CONTEXT_SUMMARY`, `CORPUS_SUMMARY`, `PRD`, `CAPABILITIES` |
| **2** | Epics + Features + Roadmap | `CAPABILITY_CARDS`, `EPICS`, `FEATURES`, **`ROADMAP`** *(new)* |
| **3** | Detailed Features (Stories) + Architecture | `USER_STORIES`, `TECHNICAL_ARCHITECTURE`, `LEAN_CANVAS` |

**Modernization difference in Phase 1:** The CAPABILITIES artifact uses the
enriched modernization prompt (pillar framework + assessment tables) instead
of the simple L0/L1/L2 hierarchy. Same artifact type, different prompt.

**Modernization difference in Phase 2:** CAPABILITY_CARDS include migration
sections. Same artifact type, enhanced prompt.

---

## Step-by-Step Implementation

### Step 1 -- Questionnaire Module

**Purpose:** Load guided intake questionnaires from JSON files, validate user
answers, and serialize them into structured prompt context.

**Source of truth:** The questionnaire definitions live in JSON files that
already exist in the repository:

- `questionnaire/greenfield.json` -- 16 questions across 5 sections
- `questionnaire/modernization.json` -- 18 questions across 7 sections

These files define sections, questions, input types, required flags, options
for selects, and -- critically -- a **`mapping` array** on each question that
uses dot-notation paths (e.g., `current_state.architecture.summary`,
`nfrs.availability`) to describe which semantic concept(s) each answer feeds.

**New file:** `prdgen/questionnaire.py`

```python
QUESTIONNAIRE_DIR = Path(__file__).parent.parent / "questionnaire"

def load_questionnaire(flow_type: str) -> dict:
    """Load questionnaire JSON from questionnaire/{flow_type}.json at runtime.
    Supports versioning and custom questionnaires without code changes."""

def get_questions(flow_type: str) -> List[dict]:
    """Return flat list of question dicts for the given flow type."""

def validate_answers(flow_type: str, answers: Dict[str, str]) -> List[str]:
    """Validate answers against schema (required fields, input types).
    Returns list of error strings (empty = valid)."""

def format_answers_as_context(flow_type: str, answers: Dict[str, str]) -> str:
    """Produce the STRUCTURED context block for LLM prompt injection.
    Uses the `mapping` field to build a nested markdown document:
    - All `current_state.*` answers grouped under `## Current State`
    - All `nfrs.*` under `## Non-Functional Requirements`
    - All `constraints.*` under `## Constraints`
    - Multi-mapped answers appear in EACH section they map to.
    """

def format_answers_as_transcript(flow_type: str, answers: Dict[str, str]) -> str:
    """Produce the RAW Q&A transcript for audit/traceability.
    Preserves original question order with section headers.
    Saved to snapshot but NOT fed to prompts."""

# Mapping hierarchy for structured context serialization:
MAPPING_SECTIONS = {
    "current_state":  "## Current State",
    "future_state":   "## Future / Target State",
    "nfrs":           "## Non-Functional Requirements",
    "constraints":    "## Constraints",
    "scope":          "## Scope",
    "migration":      "## Migration Strategy",
    "delta":          "## Delta Analysis (Current → Target)",
    "integrations":   "## Integrations & Dependencies",
    "risks":          "## Risks",
    "open_questions":  "## Open Questions",
    "objectives":     "## Objectives & Success Metrics",
    "success_metrics": "## Objectives & Success Metrics",   # merged
    "personas":       "## Personas & User Groups",
    "stakeholders":   "## Stakeholders",
    "problem_statement": "## Problem / Opportunity",
    "non_goals":      "## Non-Goals",
    "delivery_model": "## Delivery Model",
    "capabilities_current_seed": "## Current State",        # alias
    "capabilities_future_seed":  "## Future / Target State", # alias
}
```

**How the mapping-driven serialization works:**

Each question's `mapping` array contains one or more dot-paths. For a
modernization answer like:

```json
{
  "id": "mz_arch_summary",
  "mapping": ["current_state.architecture.summary"],
  "answer": "Monolithic Java app on Oracle DB, hosted on-prem..."
}
```

`format_answers_as_context()` groups this under:

```markdown
## Current State

### Architecture
Monolithic Java app on Oracle DB, hosted on-prem...
```

Multi-mapped questions (e.g., `mz_system_name_scope` → `["current_state.system_overview",
"scope.in_scope", "scope.out_of_scope"]`) have their answer placed under EACH
mapped section.

**Dual output -- what goes where:**

| Output | Purpose | Destination |
|--------|---------|-------------|
| **Structured context** (`format_answers_as_context`) | Fed to LLM prompts as part of the corpus | Prepended to docs in `PhasedFlowRunner.__init__()` |
| **Raw Q&A transcript** (`format_answers_as_transcript`) | Audit trail, human-readable record | Saved to `questionnaire_transcript.md` in snapshot dir |

**Maturity assessment:** The modernization questionnaire does NOT include explicit
maturity-rating questions. The LLM infers maturity levels (Non-Existent / Lagging /
On Par / Leading) from the `current_capabilities`, `pain_points`, `delta_priorities`,
and `target_capabilities` answers. The user corrects at the Phase 1 HITL gate.

**Key modernization questions that feed capability assessment:**

| Question ID | Mapping | Feeds |
|-------------|---------|-------|
| `mz_current_capabilities` | `capabilities_current_seed` | Part 2 "Current State" column |
| `mz_target_capabilities` | `capabilities_future_seed` | Part 2 "Desired Future State" column |
| `mz_pain_points` | `current_state.pain_points` | Maturity inference (pain → Lagging) |
| `mz_delta_priorities` | `delta.capabilities`, `delta.nfrs` | Part 3 "Gap Summary" |
| `mz_arch_summary` | `current_state.architecture.summary` | Architecture context |
| `mz_objectives` | `objectives`, `success_metrics` | Maturity target inference |

**Files changed:** None (purely additive). JSON files already exist.

---

### Step 2 -- Phase Definitions Module

**Purpose:** Define the 3 phase gates, artifact-to-phase mapping, snapshot
creation, and approval state machine.

**New file:** `prdgen/phases.py`

```python
@dataclass
class PhaseDefinition:
    number: int                          # 1, 2, 3
    name: str                            # "Foundation", "Planning", "Detail"
    label: str                           # User-facing label
    artifacts: List[ArtifactType]        # Which artifacts this phase generates
    requires_phase: Optional[int]        # Previous phase that must be approved

class PhaseStatus(str, Enum):
    PENDING     = "pending"
    GENERATING  = "generating"
    REVIEW      = "review"       # waiting for HITL approval
    APPROVED    = "approved"
    REJECTED    = "rejected"     # user sent it back with feedback

@dataclass
class PhaseSnapshot:
    phase_number: int
    artifacts: Dict[str, str]            # artifact_name -> content (frozen)
    content_hashes: Dict[str, str]       # artifact_name -> SHA-256
    approved_at: Optional[str]
    approved_by: Optional[str]
    notes: Optional[str]

PHASE_DEFINITIONS = [
    PhaseDefinition(
        number=1, name="Foundation",
        label="Context Summary + PRD + Capabilities",
        artifacts=[
            ArtifactType.CONTEXT_SUMMARY,
            ArtifactType.CORPUS_SUMMARY,
            ArtifactType.PRD,
            ArtifactType.CAPABILITIES,
        ],
        requires_phase=None,
    ),
    PhaseDefinition(
        number=2, name="Planning",
        label="Epics + Features + Roadmap",
        artifacts=[
            ArtifactType.CAPABILITY_CARDS,
            ArtifactType.EPICS,
            ArtifactType.FEATURES,
            ArtifactType.ROADMAP,
        ],
        requires_phase=1,
    ),
    PhaseDefinition(
        number=3, name="Detail",
        label="User Stories + Architecture",
        artifacts=[
            ArtifactType.USER_STORIES,
            ArtifactType.TECHNICAL_ARCHITECTURE,
            ArtifactType.LEAN_CANVAS,
        ],
        requires_phase=2,
    ),
]

def create_snapshot(phase_number, artifacts_dict) -> PhaseSnapshot
def verify_snapshot(snapshot: PhaseSnapshot) -> bool   # re-hash and compare
def get_phase_definition(phase_number) -> PhaseDefinition
def get_prior_snapshots(phase_number, session_snapshots) -> Dict[str, str]
```

**Files changed:** None (purely additive).

---

### Step 3 -- Modernization Capability Templates & Prompts

**Purpose:** Add the capmap.pdf-derived capability assessment structure for the
modernization path. This is the core differentiator between the two flows.

#### 3a. New template: `templates/Capability_Assessment_Template.md`

This markdown template encodes the structure extracted from capmap.pdf. It is
loaded by `prompt_templates.py` (same mechanism as Epic/Feature templates) and
injected into the modernization capabilities prompt.

```markdown
# Capability Assessment Framework

[Overall transformation vision statement derived from input documents]

---

## Part 1: Transformation Pillar Overview

### Pillar: [Pillar Name]
*[Mission statement: 1-2 sentences describing what this pillar achieves]*

#### L1: [Capability Name]
- L2: [Sub-capability 1]
- L2: [Sub-capability 2]
- L2: [Sub-capability 3]

[Repeat L1 blocks under each pillar]

[Repeat Pillar blocks -- typically 3-6 pillars]

---

## Part 2: Detailed Capability Assessment

### [Pillar Name]: [L1 Capability Name]

| L2 Capability | Current State | Maturity (Current) | Maturity (Target) | Desired Future State |
|---------------|---------------|-------------------|-------------------|---------------------|
| [L2 name] | [2-3 sentence description of today's pain/situation] | Non-Existent / Lagging / On Par / Leading | Non-Existent / Lagging / On Par / Leading | [2-3 sentence description of desired outcome] |

[Repeat table for each L1 capability]

---

## Part 3: Gap Summary

### Critical Gaps (Non-Existent → Leading)
- [L2 capability]: [one-line gap description]

### Major Gaps (Lagging → Leading)
- [L2 capability]: [one-line gap description]

### Incremental Improvements (On Par → Leading)
- [L2 capability]: [one-line gap description]
```

#### 3b. New template: `templates/Capability_Card_Modernization_Template.md`

Extends the existing capability card structure with migration-specific sections.

```markdown
# Modernization Capability Card Template

## [L1 Capability Name]

**Description**
- [what this capability does]

**Objective**
- [measurable business outcome]

**Primary Personas**
- [affected user types]

**Secondary Personas**
- [secondary stakeholders]

**Current State Assessment**
- [summary of current state from capability assessment]
- Current Maturity: [level]

**Design Considerations**
- [product + system-level constraints/tradeoffs]

**Success Signals**
- [measurable indicators of capability improvement]

**Migration Approach**
- Recommended pattern: [strangler-fig / big-bang / parallel-run / phased]
- Rationale: [why this approach fits this capability]

**Quick Wins** (achievable in 0-3 months)
- [immediate improvement 1]
- [immediate improvement 2]

**Long-term Investments** (3-12+ months)
- [sustained effort 1]
- [sustained effort 2]

**Legacy Dependencies to Decommission**
- [system/component 1]: [decommission trigger condition]
- [system/component 2]: [decommission trigger condition]

**Transition Risks & Mitigations**
| Risk | Impact | Mitigation |
|------|--------|------------|
| [risk 1] | [H/M/L] | [mitigation] |

**Related L2 (from capability map)**
- [L2 sub-capability references]
```

#### 3c. Modify: `prdgen/prompt_templates.py`

Add template loading for the two new templates + a new system prompt.

```diff
  template_files = {
      "epic": "Epic_Template.md",
      "feature": "Feature_Template.md",
      "user_story": "User_Story_Template.md",
+     "capability_assessment": "Capability_Assessment_Template.md",
+     "capability_card_modernization": "Capability_Card_Modernization_Template.md",
  }

  SYSTEM_PROMPTS = {
      ...
+     "capabilities_modernization": """You produce a modernization capability
+ assessment framework derived from the PRD and intake context.
+
+ Rules:
+ - Derive transformation pillars from the domain described in the documents.
+   Do NOT use generic/fixed pillar names -- they must reflect the actual
+   business domain being modernized.
+ - For Current State: base descriptions on explicit pain points, constraints,
+   and current-system descriptions from the input documents.
+ - For Maturity ratings: use ONLY these four levels:
+   Non-Existent, Lagging, On Par, Leading.
+ - For Desired Future State: derive from goals, vision, and desired outcomes
+   in the documents. Do NOT invent aspirations not supported by the inputs.
+ - If information is insufficient to rate a capability, mark maturity as
+   "Unknown" and flag in the Gap Summary.
+ - Include Part 3 (Gap Summary) to highlight the biggest current→target deltas.
+
+ Output requirements:
+ - Follow the Capability Assessment Template structure exactly.
+ - All three parts (Pillar Overview, Detailed Assessment, Gap Summary) are
+   required.""",
  }
```

**Lines changed:** ~30 lines added to `prompt_templates.py`.

#### 3d. Modify: `prdgen/prompts.py`

Add two new prompt functions:

```python
def capabilities_modernization_prompt(
    prd_markdown: str,
    context_summary_md: str,
    intake_context_md: str,           # from questionnaire (includes current_capabilities + desired_outcomes)
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
- Group gaps by severity: Critical (Non-Existent→Leading), Major (Lagging→Leading),
  Incremental (On Par→Leading)
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
```

**Lines changed in prompts.py:** ~80 lines added (two new functions).

#### 3e. Modify: `prdgen/capability_cards.py`

Add modernization card parsing/validation alongside existing greenfield functions.

```python
# NEW: Extract L1 names from modernization capability assessment
# (different format: tables with "### Pillar: L1 Name" headers)
def extract_l1_names_modernization(capabilities_md: str) -> List[str]:
    """Extract L1 names from modernization assessment (### [Pillar]: [L1 Name])."""
    # Parses the Part 2 table headers
    names = re.findall(r"^###\s+.+?:\s+(.+)$", capabilities_md, flags=re.MULTILINE)
    ...

# NEW: Ensure modernization cards have migration sections
def ensure_modernization_cards(cards_md: str, l1_names: List[str]) -> str:
    """Validate modernization cards have migration sections, add TBD if missing."""
    ...
```

**Lines changed in capability_cards.py:** ~40 lines added.

#### 3f. Modify: `prdgen/generator.py`

Add flow-type-aware routing in `generate_capabilities()` and
`generate_capability_cards()`. This is the minimal touch to existing generator
methods.

```python
# In generate_capabilities():
def generate_capabilities(self) -> str:
    artifact_type = ArtifactType.CAPABILITIES
    if self.cache.has(artifact_type):
        ...  # unchanged

    prd_md = self.generate_prd()

    # NEW: Route to modernization prompt if flow_type is modernization
    if self.cfg.flow_type == "modernization":
        context_md = self.cache.get(ArtifactType.CONTEXT_SUMMARY) or ""
        intake_md = self._get_intake_context()  # from questionnaire answers in cfg
        caps_md = _run_step(
            self.loaded,
            SYSTEM_CAPS_MODERNIZATION,    # new system prompt
            capabilities_modernization_prompt(prd_md, context_md, intake_md),
            self.cfg,
            max_new_tokens=2000,          # larger: assessment tables are verbose
            temperature=max(self.cfg.temperature - 0.2, 0.3),
            step_name="capabilities_modernization",
        )
    else:
        caps_md = _run_step(...)  # existing greenfield path, UNCHANGED

    ...  # rest of method unchanged


# In generate_capability_cards():
def generate_capability_cards(self) -> str:
    ...
    if self.cfg.flow_type == "modernization":
        l1_names = extract_l1_names_modernization(caps_md)
        intake_md = self._get_intake_context()
        cards_md = _run_step(
            self.loaded,
            SYSTEM_CAPS_MODERNIZATION,
            capability_cards_modernization_prompt(prd_md, caps_md, l1_names, intake_md),
            ...
        )
        cards_md = ensure_modernization_cards(cards_md, l1_names)
    else:
        ...  # existing greenfield path, UNCHANGED


# NEW helper:
def _get_intake_context(self) -> str:
    """Get formatted questionnaire context from config."""
    if self.cfg.questionnaire_answers:
        from .questionnaire import format_answers_as_context
        return format_answers_as_context(self.cfg.flow_type, self.cfg.questionnaire_answers)
    return ""
```

**Lines changed in generator.py:** ~50 lines added (routing logic + helper).
Existing greenfield paths are inside `else` branches -- **zero changes** to them.

#### Summary for Step 3

| File | Change | Lines |
|------|--------|-------|
| `templates/Capability_Assessment_Template.md` | **NEW** | ~60 |
| `templates/Capability_Card_Modernization_Template.md` | **NEW** | ~55 |
| `prdgen/prompt_templates.py` | Add template loading + system prompt | ~30 |
| `prdgen/prompts.py` | Add 2 modernization prompt functions | ~80 |
| `prdgen/capability_cards.py` | Add modernization parsing/validation | ~40 |
| `prdgen/generator.py` | Add flow-type routing in 2 methods + helper | ~50 |

---

### Step 4 -- Roadmap Artifact

**Purpose:** Add the `ROADMAP` artifact type -- a prioritised delivery timeline
derived from approved epics and features.

#### 4a. New file: `prdgen/roadmap.py`

```python
def validate_roadmap_structure(md: str) -> bool
def extract_phases_from_roadmap(md: str) -> List[dict]
```

#### 4b. Modify: `prdgen/artifact_types.py`

```diff
  class ArtifactType(str, Enum):
      ...
      TECHNICAL_ARCHITECTURE = "technical_architecture"
+     ROADMAP = "roadmap"

  ARTIFACT_SETS["development"].add(ArtifactType.ROADMAP)
  ARTIFACT_SETS["complete"].add(ArtifactType.ROADMAP)

+ ARTIFACT_NAMES[ArtifactType.ROADMAP] = "Delivery Roadmap"
+ ARTIFACT_FILENAMES[ArtifactType.ROADMAP] = "roadmap.md"
```

#### 4c. Modify: `prdgen/dependencies.py`

```diff
  DEPENDENCIES[ArtifactType.ROADMAP] = [
      ArtifactType.PRD,
      ArtifactType.EPICS,
      ArtifactType.FEATURES,
  ]

  GENERATION_ORDER:  insert ROADMAP after FEATURES, before USER_STORIES
```

#### 4d. Modify: `prdgen/prompts.py`

Add `roadmap_prompt(prd_md, epics_md, features_md) -> str` -- the LLM produces:
- Release phases (MVP / Phase 1 / Phase 2 / Phase 3)
- Epic-to-phase mapping with rationale
- Dependencies and critical path
- Risk-adjusted timeline considerations

For modernization, a `roadmap_modernization_prompt()` variant that adds:
- Migration wave sequencing
- Legacy decommission milestones
- Parallel-run / cutover gates

#### 4e. Modify: `prdgen/generator.py`

Add `generate_roadmap()` (~30 lines, follows `generate_lean_canvas()` pattern).
Add entry to `generator_map` dict in `generate_selected()`.

**Summary:** 1 new file + 4 minimal edits.

---

### Step 5 -- Config Additions

**Modify:** `prdgen/config.py`

```diff
  @dataclass
  class GenerationConfig:
      ...
+     # Phased generation (opt-in, default=False preserves existing behavior)
+     phase_mode: bool = False
+     flow_type: str = "greenfield"               # "greenfield" | "modernization"
+     questionnaire_answers: Optional[Dict[str, str]] = None
+     current_phase: Optional[int] = None          # 1, 2, or 3
+     prior_snapshot_dir: Optional[Path] = None    # where to load approved snapshots
```

All defaults preserve existing behavior. `phase_mode=False` means all existing
CLI commands, API endpoints, and tests continue working identically.

**Files changed:** 1 file, ~6 lines added.

---

### Step 6 -- Flow Orchestrator

**Purpose:** Top-level orchestrator that ties questionnaires -> phases -> existing
generators. Handles two-path flow logic and phase gate pauses.

**New file:** `prdgen/flows.py`

```python
class FlowType(str, Enum):
    GREENFIELD     = "greenfield"
    MODERNIZATION  = "modernization"

class PhasedFlowRunner:
    """
    Orchestrates phased generation with HITL gates.

    Usage:
        runner = PhasedFlowRunner(flow_type, questionnaire_answers, cfg, loaded, docs)

        # Phase 1 -- generates, returns artifacts for review
        phase1_artifacts = runner.run_phase(1)
        # ... user reviews, possibly edits maturity ratings ...
        runner.approve_phase(1, approved_by="user@co.com", notes="...")

        # Phase 2
        phase2_artifacts = runner.run_phase(2)
        runner.approve_phase(2, ...)

        # Phase 3
        phase3_artifacts = runner.run_phase(3)
        runner.approve_phase(3, ...)

        final = runner.get_all_approved_artifacts()
    """

    def __init__(self, flow_type, questionnaire_answers, cfg, loaded, docs):
        # 1. Store flow_type and answers on cfg
        #    cfg.flow_type = flow_type
        #    cfg.questionnaire_answers = questionnaire_answers
        # 2. Load questionnaire JSON from questionnaire/{flow_type}.json
        # 3. Produce BOTH outputs from answers:
        #    a. structured_context = format_answers_as_context(flow_type, answers)
        #       → mapping-driven nested markdown (for LLM prompts)
        #    b. raw_transcript = format_answers_as_transcript(flow_type, answers)
        #       → raw Q&A in section order (saved to snapshot for audit)
        # 4. Create a synthetic IngestedDoc from structured_context
        #    and PREPEND it to the docs list (enriches corpus for all prompts)
        # 5. Create ArtifactGenerator with enriched docs
        # 6. Initialise empty snapshots dict
        # 7. Store raw_transcript for later snapshot inclusion

    def run_phase(self, phase_number: int) -> Dict[ArtifactType, str]:
        # 1. Validate prior phase is approved (if required)
        # 2. Seed the generator's cache with all prior snapshot artifacts
        #    (approved artifacts become cache hits -- generator skips regen)
        # 3. Get phase definition -> artifact list
        # 4. Set cfg.generate_only to this phase's artifacts
        # 5. Call generator.generate_selected()
        # 6. Return artifacts for review

    def approve_phase(self, phase_number, approved_by, notes="",
                      edited_artifacts: Dict[str, str] = None):
        # 1. If edited_artifacts provided (HITL edits), replace content
        #    in the generator's cache (this is how user maturity overrides
        #    flow into Phase 2)
        # 2. Create PhaseSnapshot with SHA-256 hashes
        # 3. Store in self.snapshots[phase_number]
        # 4. Freeze artifact files to snapshot directory

    def reject_phase(self, phase_number, feedback):
        # 1. Mark phase rejected, store feedback
        # 2. Invalidate cache for this phase's artifacts
        # 3. User calls run_phase() again to re-generate

    def get_snapshot(self, phase_number) -> PhaseSnapshot
    def get_all_approved_artifacts(self) -> Dict[ArtifactType, str]
```

**Key design: HITL edits flow forward via cache.**

When the user edits the capabilities maturity ratings at the Phase 1 gate:
1. Frontend sends the edited CAPABILITIES markdown in the approve request
2. `approve_phase()` receives it via `edited_artifacts`
3. The edited content replaces the LLM-generated version in the cache
4. The snapshot is created from the edited version (SHA-256 of edited content)
5. When Phase 2 runs, the cache seed contains the user-edited capabilities
6. `generate_epics()` calls `generate_capabilities()` -> cache hit -> returns
   the user-edited version
7. Epics are generated against the user-approved capability assessment

**Files changed:** None (purely additive).

---

### Step 7 -- SQLite Persistence Layer (Backend)

**Purpose:** Provide durable persistence for the entire phased flow so that
sessions survive server restarts, every state transition is recoverable, and
every approval/edit has an audit trail. The existing `JobTracker` (JSON) is
untouched; phased sessions use a parallel SQLite store.

**New file:** `backend/app/phase_store.py`

#### Schema (8 tables)

```sql
-- ============================================================
-- TABLE 1: Sessions (top-level container)
-- ============================================================
CREATE TABLE sessions (
    id                TEXT PRIMARY KEY,          -- UUID
    flow_type         TEXT NOT NULL,             -- 'greenfield' | 'modernization'
    status            TEXT NOT NULL DEFAULT 'intake',
                      -- 'intake' | 'questionnaire_done' | 'docs_uploaded'
                      -- | 'phase_1' | 'phase_2' | 'phase_3' | 'completed' | 'failed'
    questionnaire_ver TEXT,                      -- version from JSON (e.g. "v1")
    input_dir         TEXT,                      -- path to uploaded documents
    output_dir        TEXT,                      -- base path for generation output
    snapshot_base_dir TEXT,                      -- base path for phase snapshots
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- ============================================================
-- TABLE 2: Questionnaire Responses
-- ============================================================
CREATE TABLE questionnaire_responses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question_id     TEXT NOT NULL,               -- e.g. "mz_pain_points"
    question_text   TEXT NOT NULL,               -- stored for audit (question can evolve)
    answer          TEXT NOT NULL,
    mapping         TEXT,                        -- JSON array of dot-paths, stored for traceability
    created_at      TEXT NOT NULL,
    UNIQUE(session_id, question_id)
);

-- ============================================================
-- TABLE 3: Session Documents (uploaded files)
-- ============================================================
CREATE TABLE session_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_size       INTEGER,
    file_type       TEXT,                        -- 'txt' | 'md' | 'docx'
    content_hash    TEXT,                        -- SHA-256 of file content
    uploaded_at     TEXT NOT NULL
);

-- ============================================================
-- TABLE 4: Phase Gates (one row per phase per session)
-- ============================================================
CREATE TABLE phase_gates (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    phase_number        INTEGER NOT NULL CHECK (phase_number IN (1, 2, 3)),
    phase_name          TEXT NOT NULL,            -- 'Foundation' | 'Planning' | 'Detail'
    status              TEXT NOT NULL DEFAULT 'pending',
                        -- 'pending' | 'generating' | 'review' | 'approved' | 'rejected'
    overall_progress    INTEGER DEFAULT 0,        -- 0-100, persisted for resume
    started_at          TEXT,
    generated_at        TEXT,                     -- when generation finished (entered review)
    completed_at        TEXT,                     -- when approved or rejected
    approved_by         TEXT,
    approval_notes      TEXT,
    rejection_feedback  TEXT,
    rejection_count     INTEGER DEFAULT 0,        -- how many times rejected before approved
    snapshot_dir        TEXT,                     -- path to frozen artifact directory
    UNIQUE(session_id, phase_number)
);

-- ============================================================
-- TABLE 5: Generation Progress (per-artifact within a phase)
-- Survives server restart; replaces in-memory job_progress dict
-- ============================================================
CREATE TABLE generation_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_gate_id   INTEGER NOT NULL REFERENCES phase_gates(id) ON DELETE CASCADE,
    artifact_type   TEXT NOT NULL,               -- e.g. 'prd', 'capabilities'
    status          TEXT NOT NULL DEFAULT 'pending',
                    -- 'pending' | 'generating' | 'completed' | 'failed' | 'cached'
    progress_pct    INTEGER DEFAULT 0,           -- 0-100 for this artifact
    message         TEXT,                        -- human-readable status message
    started_at      TEXT,
    completed_at    TEXT,
    char_count      INTEGER,                     -- output size
    generation_ms   INTEGER,                     -- wall-clock generation time
    error_message   TEXT,                        -- if status='failed'
    UNIQUE(phase_gate_id, artifact_type)
);

-- ============================================================
-- TABLE 6: Phase Artifacts (final outputs per phase)
-- ============================================================
CREATE TABLE phase_artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_gate_id   INTEGER NOT NULL REFERENCES phase_gates(id) ON DELETE CASCADE,
    artifact_type   TEXT NOT NULL,
    content_hash    TEXT NOT NULL,                -- SHA-256 of content
    file_path       TEXT NOT NULL,
    char_count      INTEGER,
    was_edited      BOOLEAN DEFAULT FALSE,       -- TRUE if user edited at HITL gate
    created_at      TEXT NOT NULL,
    UNIQUE(phase_gate_id, artifact_type)
);

-- ============================================================
-- TABLE 7: Artifact Edits (audit trail for HITL modifications)
-- ============================================================
CREATE TABLE artifact_edits (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_artifact_id   INTEGER NOT NULL REFERENCES phase_artifacts(id) ON DELETE CASCADE,
    original_hash       TEXT NOT NULL,            -- SHA-256 of LLM-generated content
    edited_hash         TEXT NOT NULL,            -- SHA-256 of user-edited content
    original_file_path  TEXT NOT NULL,            -- backup of original before edit
    edited_by           TEXT NOT NULL,
    edit_summary        TEXT,                     -- user-provided reason for changes
    edited_at           TEXT NOT NULL
);

-- ============================================================
-- TABLE 8: Audit Log (immutable event stream)
-- ============================================================
CREATE TABLE audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
                    -- 'session_created'     | 'questionnaire_submitted'
                    -- | 'docs_uploaded'     | 'phase_generation_started'
                    -- | 'artifact_generated'| 'artifact_cached'
                    -- | 'phase_review_ready'| 'phase_approved'
                    -- | 'phase_rejected'    | 'artifact_edited'
                    -- | 'snapshot_created'  | 'session_completed'
    phase_number    INTEGER,                     -- NULL for session-level events
    artifact_type   TEXT,                        -- NULL for phase/session-level events
    actor           TEXT,                        -- who triggered (user email or 'system')
    detail          TEXT,                        -- JSON blob with event-specific data
    created_at      TEXT NOT NULL
);

CREATE INDEX idx_audit_session ON audit_log(session_id, created_at);
CREATE INDEX idx_audit_event   ON audit_log(event_type, created_at);
```

#### Persistence Touchpoints (where every DB write happens in the flow)

```
USER ACTION / SYSTEM EVENT            DB WRITES
──────────────────────────            ─────────

1. POST /v2/sessions
   User picks greenfield              → INSERT sessions (status='intake')
   or modernization                   → INSERT audit_log (session_created)

2. POST /v2/sessions/{id}/questionnaire
   User submits answers               → INSERT questionnaire_responses (one per Q)
                                      → UPDATE sessions (status='questionnaire_done',
                                         questionnaire_ver=json version)
                                      → INSERT audit_log (questionnaire_submitted)

3. POST /v2/sessions/{id}/upload
   User uploads documents             → INSERT session_documents (one per file)
                                      → UPDATE sessions (status='docs_uploaded',
                                         input_dir=path)
                                      → INSERT audit_log (docs_uploaded,
                                         detail={filenames, sizes})

4. POST /v2/sessions/{id}/phases/1/generate
   System begins Phase 1              → INSERT phase_gates (phase=1, status='generating')
                                      → INSERT generation_progress (one per artifact
                                         in phase, status='pending')
                                      → UPDATE sessions (status='phase_1')
                                      → INSERT audit_log (phase_generation_started)

   [LLM starts artifact]             → UPDATE generation_progress
                                         (status='generating', started_at=now)

   [LLM completes artifact]          → UPDATE generation_progress
                                         (status='completed', char_count, generation_ms)
                                      → INSERT audit_log (artifact_generated,
                                         detail={type, chars, ms})
                                      → Write .md file to disk (incremental save)

   [Artifact served from cache]       → UPDATE generation_progress
                                         (status='cached')
                                      → INSERT audit_log (artifact_cached)

   [Phase generation done]            → UPDATE phase_gates (status='review',
                                         generated_at=now, overall_progress=100)
                                      → INSERT phase_artifacts (one per artifact)
                                      → INSERT audit_log (phase_review_ready)

   [Phase generation FAILS]           → UPDATE generation_progress
                                         (status='failed', error_message)
                                      → UPDATE phase_gates (status='failed')
                                      → INSERT audit_log (phase_generation_failed)

5. GET /v2/sessions/{id}/phases/1/review
   User reviews artifacts             → (reads only, no writes)

6. POST /v2/sessions/{id}/phases/1/approve
   User approves (with optional       → UPDATE phase_gates (status='approved',
   edited artifacts)                      approved_by, completed_at=now)
                                      → INSERT audit_log (phase_approved)

   IF edited_artifacts provided:       → Backup original file to {snapshot}/originals/
                                      → Write edited content to artifact file
                                      → UPDATE phase_artifacts
                                         (content_hash=new_hash, was_edited=TRUE)
                                      → INSERT artifact_edits
                                         (original_hash, edited_hash, edited_by)
                                      → INSERT audit_log (artifact_edited,
                                         detail={type, original_hash, edited_hash})

   Create snapshot:                   → Copy artifacts to snapshot dir
                                      → UPDATE phase_gates (snapshot_dir=path)
                                      → INSERT audit_log (snapshot_created,
                                         detail={hashes})

7. POST /v2/sessions/{id}/phases/1/reject
   User rejects with feedback         → UPDATE phase_gates (status='rejected',
                                         rejection_feedback, rejection_count++)
                                      → INSERT audit_log (phase_rejected,
                                         detail={feedback})
                                      (user can POST /generate again →
                                       new generation_progress rows created)

8. POST /v2/sessions/{id}/phases/2/generate
   System begins Phase 2              → (same pattern as step 4)
                                      → Additionally: loads Phase 1 snapshot from
                                         phase_gates.snapshot_dir + phase_artifacts
                                         to seed the generator cache

9. [After Phase 3 approved]
   Session complete                   → UPDATE sessions (status='completed')
                                      → INSERT audit_log (session_completed)
```

#### Resumability

Because all progress is in SQLite (not in-memory), the system can resume after
a server restart:

| Scenario | Recovery |
|----------|----------|
| Server crashes mid-generation | `phase_gates.status='generating'` + `generation_progress` rows show which artifacts completed. `PhaseService.start_phase()` checks for this state and resumes from the last incomplete artifact. |
| Server restarts after generation, before review | `phase_gates.status='review'` + `phase_artifacts` rows intact. Review endpoint reads from DB + disk. |
| Server restarts after approval, before next phase | `phase_gates.status='approved'` + `snapshot_dir` points to frozen files. Next phase loads snapshot normally. |

#### Python class

```python
class PhaseStore:
    def __init__(self, db_path: Path):
        # Creates DB + all 8 tables if not exists
        # Enables WAL mode for concurrent reads during generation
        # Enables foreign keys

    # --- Session lifecycle ---
    def create_session(self, session_id: str, flow_type: str) -> dict
    def get_session(self, session_id: str) -> Optional[dict]
    def update_session(self, session_id: str, **kwargs)
    def list_sessions(self, status: str = None, limit: int = 50) -> list

    # --- Questionnaire ---
    def save_questionnaire(self, session_id: str, questions: list, answers: dict)
        # Stores question_text + mapping alongside answer for audit
    def get_questionnaire(self, session_id: str) -> dict

    # --- Documents ---
    def save_document(self, session_id: str, filename: str, file_path: str,
                      file_size: int, file_type: str, content_hash: str)
    def get_documents(self, session_id: str) -> list

    # --- Phase gates ---
    def create_phase_gate(self, session_id: str, phase_number: int,
                          phase_name: str) -> dict
    def update_phase_gate(self, session_id: str, phase_number: int, **kwargs)
    def get_phase_gate(self, session_id: str, phase_number: int) -> Optional[dict]
    def get_all_phase_gates(self, session_id: str) -> list

    # --- Generation progress ---
    def init_generation_progress(self, phase_gate_id: int,
                                 artifact_types: list)
    def update_artifact_progress(self, phase_gate_id: int,
                                 artifact_type: str, **kwargs)
    def get_generation_progress(self, phase_gate_id: int) -> list
    def get_incomplete_artifacts(self, phase_gate_id: int) -> list
        # For resume: returns artifacts not yet 'completed' or 'cached'

    # --- Phase artifacts ---
    def save_phase_artifact(self, phase_gate_id: int, artifact_type: str,
                            content_hash: str, file_path: str,
                            char_count: int, was_edited: bool = False)
    def get_phase_artifacts(self, session_id: str, phase_number: int) -> list
    def update_phase_artifact(self, phase_gate_id: int,
                              artifact_type: str, **kwargs)

    # --- Artifact edits ---
    def save_artifact_edit(self, phase_artifact_id: int,
                           original_hash: str, edited_hash: str,
                           original_file_path: str, edited_by: str,
                           edit_summary: str = None)
    def get_artifact_edits(self, session_id: str, phase_number: int) -> list

    # --- Audit log ---
    def log_event(self, session_id: str, event_type: str,
                  phase_number: int = None, artifact_type: str = None,
                  actor: str = 'system', detail: dict = None)
    def get_audit_log(self, session_id: str, event_type: str = None,
                      limit: int = 200) -> list

    # --- Full session export (for debugging / support) ---
    def export_session(self, session_id: str) -> dict
        # Returns everything: session + questionnaire + documents +
        # all phase gates + all artifacts + all edits + full audit log
```

**Files changed:** None (purely additive). DB: `backend/phases.db` (auto-created).

---

### Step 8 -- Phase API Service

**Purpose:** Wraps `PhasedFlowRunner` for the FastAPI backend. Every method
orchestrates both the generation logic AND the persistence writes.

**New file:** `backend/app/services/phase_service.py`

```python
class PhaseService:
    def __init__(self, phase_store: PhaseStore):
        self.store = phase_store

    def create_session(self, flow_type: str) -> dict:
        # 1. Generate UUID
        # 2. store.create_session(id, flow_type)
        # 3. store.log_event(session_created)
        # 4. Load questionnaire JSON via prdgen.questionnaire
        # 5. Return { session_id, flow_type, questionnaire }

    def submit_questionnaire(self, session_id: str, answers: dict) -> dict:
        # 1. Load questionnaire JSON to get question_text + mapping per Q
        # 2. Validate answers via prdgen.questionnaire.validate_answers()
        # 3. store.save_questionnaire(session_id, questions, answers)
        # 4. store.update_session(status='questionnaire_done')
        # 5. store.log_event(questionnaire_submitted)
        # 6. Return { status, next_action: 'upload' }

    def upload_documents(self, session_id: str, files: list) -> dict:
        # 1. Save files to session input_dir
        # 2. For each file: hash content, store.save_document(...)
        # 3. store.update_session(status='docs_uploaded', input_dir=path)
        # 4. store.log_event(docs_uploaded, detail={filenames})
        # 5. Return { status, file_count }

    def start_phase(self, session_id: str, phase_number: int) -> str:
        # 1. Validate prerequisites:
        #    - Session status allows this phase
        #    - Prior phase is approved (if required)
        #    - Check for resumable interrupted generation
        # 2. Load questionnaire answers from DB
        # 3. Load prior phase snapshot artifacts from DB + disk
        # 4. store.create_phase_gate(session_id, phase_number, phase_name)
        # 5. store.init_generation_progress(gate_id, artifact_types)
        # 6. store.update_session(status=f'phase_{phase_number}')
        # 7. store.log_event(phase_generation_started)
        # 8. Launch PhasedFlowRunner.run_phase() in background thread
        #    with a progress_callback that calls:
        #      store.update_artifact_progress(...)
        #      store.log_event(artifact_generated | artifact_cached)
        # 9. On completion: store.update_phase_gate(status='review')
        #    + store.save_phase_artifact() for each artifact
        #    + store.log_event(phase_review_ready)
        # 10. On failure: store.update_phase_gate(status='failed')
        #    + store.log_event(phase_generation_failed)
        # 11. Return job_id for progress polling

    def get_phase_progress(self, session_id: str, phase_number: int) -> dict:
        # 1. store.get_phase_gate() for overall status
        # 2. store.get_generation_progress() for per-artifact detail
        # 3. Return { overall_status, overall_progress,
        #             artifacts: { type: { status, progress, message } } }
        # NOTE: reads from SQLite, NOT from in-memory dict.
        #       Survives server restart.

    def get_phase_review(self, session_id: str, phase_number: int) -> dict:
        # 1. store.get_phase_artifacts() for file paths
        # 2. Read artifact content from disk
        # 3. Determine editable artifacts based on flow_type + phase
        # 4. Return { phase, flow_type, artifacts, editable }

    def approve_phase(self, session_id: str, phase_number: int,
                      approved_by: str, notes: str,
                      edited_artifacts: Dict[str, str] = None) -> dict:
        # 1. Validate phase is in 'review' status
        # 2. If edited_artifacts:
        #    a. For each edited artifact:
        #       - Read original from disk, compute original_hash
        #       - Backup original to {snapshot_dir}/originals/{type}_original.md
        #       - Write edited content to artifact file
        #       - Compute edited_hash
        #       - store.update_phase_artifact(was_edited=True, content_hash=edited_hash)
        #       - store.save_artifact_edit(original_hash, edited_hash, ...)
        #       - store.log_event(artifact_edited)
        # 3. Create snapshot directory, copy all artifacts
        # 4. Save raw Q&A transcript to snapshot dir
        # 5. store.update_phase_gate(status='approved', snapshot_dir=path, ...)
        # 6. store.log_event(phase_approved)
        # 7. store.log_event(snapshot_created, detail={all hashes})
        # 8. If phase_number == 3:
        #       store.update_session(status='completed')
        #       store.log_event(session_completed)
        # 9. Return { status, snapshot_hash, next_phase }

    def reject_phase(self, session_id: str, phase_number: int,
                     feedback: str) -> dict:
        # 1. store.update_phase_gate(status='rejected',
        #       rejection_feedback=feedback, rejection_count++)
        # 2. store.log_event(phase_rejected, detail={feedback})
        # 3. Return { status, can_regenerate: True }

    def get_session_summary(self, session_id: str) -> dict:
        # Full read from DB: session + all phases + all artifacts + audit log
        # Calls store.export_session()

    def resume_interrupted(self, session_id: str) -> Optional[dict]:
        # Check for phase_gates with status='generating'
        # If found: get_incomplete_artifacts() and resume generation
        # from where it left off (cache has completed artifacts)
```

**Files changed:** None (purely additive).

---

### Step 9 -- New API Endpoints

**Modify:** `backend/app/main.py` (additive only, appended at bottom)

All new endpoints under `/api/v2/` -- existing `/api/` untouched.

```
POST   /api/v2/sessions
       Body: { "flow_type": "greenfield" | "modernization" }
       Returns: { session_id, flow_type, questionnaire: [...questions] }

POST   /api/v2/sessions/{id}/questionnaire
       Body: { "answers": { "key": "value", ... } }
       Returns: { status: "ready", next_phase: 1 }

POST   /api/v2/sessions/{id}/upload
       Files: multipart upload
       Returns: { status: "uploaded", file_count: N }

POST   /api/v2/sessions/{id}/phases/{n}/generate
       Returns: { status: "generating", progress_url: "..." }

GET    /api/v2/sessions/{id}/phases/{n}/status
       Returns: { status, progress, current_artifact, artifacts: {...} }

GET    /api/v2/sessions/{id}/phases/{n}/review
       Returns: { phase, flow_type, artifacts: { "prd": "...", ... },
                  editable: ["capabilities"] }
       (editable list tells UI which artifacts support HITL editing)

POST   /api/v2/sessions/{id}/phases/{n}/approve
       Body: { "approved_by": "...", "notes": "...",
               "edited_artifacts": { "capabilities": "...edited md..." } }
       Returns: { status: "approved", snapshot_hash, next_phase }

POST   /api/v2/sessions/{id}/phases/{n}/reject
       Body: { "feedback": "..." }
       Returns: { status: "rejected", can_regenerate: true }

GET    /api/v2/sessions/{id}/snapshots
       Returns: { phases: [{ number, status, artifacts, hashes, was_edited }] }

GET    /api/v2/sessions/{id}/snapshots/{n}/download
       Returns: ZIP of frozen phase artifacts

GET    /api/v2/sessions
       Returns: { sessions: [...] }
```

**Key endpoint: approve with edits.** The `/approve` endpoint accepts an optional
`edited_artifacts` dict. For the modernization path at Phase 1, the UI would
let the user edit the capabilities maturity table, then send:

```json
{
  "approved_by": "donald@co.com",
  "notes": "Adjusted 3 maturity ratings based on team input",
  "edited_artifacts": {
    "capabilities": "# Capability Assessment Framework\n...(edited markdown)..."
  }
}
```

The Phase 2 generation then uses the user-approved (possibly edited) capabilities
as its input, not the raw LLM output.

**Files changed:** 1 file modified (additive), 1 new file for Pydantic models.

---

## File Change Summary

### New Files (9)

| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `prdgen/questionnaire.py` | JSON loader + validator + mapping-driven serializer | ~220 |
| `prdgen/phases.py` | Phase definitions + snapshot management | ~180 |
| `prdgen/roadmap.py` | Roadmap validation utilities | ~60 |
| `prdgen/flows.py` | Two-path flow orchestrator | ~220 |
| `templates/Capability_Assessment_Template.md` | Modernization capmap structure (from PDF) | ~60 |
| `templates/Capability_Card_Modernization_Template.md` | Migration-enriched card template | ~55 |
| `backend/app/phase_store.py` | SQLite persistence (8 tables) for sessions/phases/artifacts/audit | ~350 |
| `backend/app/services/phase_service.py` | Phase lifecycle service with full persistence orchestration | ~250 |
| `backend/app/models/phase_models.py` | Pydantic request/response models | ~80 |

### Pre-existing Files (used as-is, not modified)

| File | Role |
|------|------|
| `questionnaire/greenfield.json` | Greenfield intake: 16 questions, 5 sections |
| `questionnaire/modernization.json` | Modernization intake: 18 questions, 7 sections |

### Modified Files (7)

| File | Change | Lines added |
|------|--------|-------------|
| `prdgen/config.py` | Add 5 new fields with safe defaults | ~6 |
| `prdgen/artifact_types.py` | Add ROADMAP enum + dict entries | ~10 |
| `prdgen/dependencies.py` | Add ROADMAP to DEPENDENCIES + ORDER | ~8 |
| `prdgen/prompts.py` | Add `roadmap_prompt()` + 2 modernization prompts | ~130 |
| `prdgen/prompt_templates.py` | Add template loading + modernization system prompt | ~30 |
| `prdgen/capability_cards.py` | Add modernization parsing/validation | ~40 |
| `prdgen/generator.py` | Add `generate_roadmap()` + flow-type routing + helper | ~85 |
| `backend/app/main.py` | Add v2 endpoints (appended at bottom) | ~100 |

### Unchanged (everything else)

All existing functionality preserved:

- `prdgen/cli.py` -- untouched
- `prdgen/model.py` -- untouched
- `prdgen/ingest.py` -- untouched
- `prdgen/context_summary.py` -- untouched
- `prdgen/architecture.py` -- untouched
- `prdgen/epics.py`, `features.py`, `stories.py` -- untouched
- `prdgen/recommendation.py` -- untouched
- `prdgen/utils.py` -- untouched
- `prdgen/formatters/` -- untouched
- `prdgen/schemas/` -- untouched
- `backend/app/job_tracker.py` -- untouched
- `backend/app/services/prd_service.py` -- untouched
- All existing tests -- untouched
- `templates/Epic_Template.md`, `Feature_Template.md`, `User_Story_Template.md` -- untouched

---

## Suggested Implementation Order

```
 Parallel track A              Parallel track B           Parallel track C
 ──────────────                ──────────────             ──────────────
 Step 1: questionnaire.py      Step 2: phases.py          Step 7: phase_store.py
         (standalone)                  (standalone)               (standalone)
         │                             │                          │
         ├─────────────────────────────┤                          │
         │                                                        │
 Step 3: Modernization templates + prompts                        │
         (depends on nothing -- just files + prompts)             │
         │                                                        │
 Step 4: Roadmap artifact                                         │
         (4 minimal file edits)                                   │
         │                                                        │
 Step 5: config.py additions                                      │
         (trivial, needed before Step 6)                          │
         │                                                        │
         ├────────────────────────────────────────────────────────┤
         │
 Step 6: flows.py              (depends on Steps 1-5)
         │
 Step 8: phase_service.py      (depends on Steps 6, 7)
         │
 Step 9: main.py endpoints     (depends on Step 8)
```

---

## How the Modernization Flow Differs from Greenfield

```
                    GREENFIELD                          MODERNIZATION
                    ──────────                          ──────────────
Questionnaire:      greenfield.json                     modernization.json
                    16 Qs / 5 sections                  18 Qs / 7 sections
                    (Product Framing, Scope,            (Current System, Drivers,
                     Constraints, People, Risks)         Architecture, Target State,
                                                         Migration, People, Deltas)

Context injection:  Mapping-driven structured context   Mapping-driven structured context
(via `mapping`      ## Problem / Opportunity            ## Current State
 field on each Q)   ## Personas & User Groups             ### System Overview
                    ## Scope                               ### Capabilities
                      ### MVP                              ### Pain Points
                      ### Future Phases                    ### Architecture
                    ## Constraints                       ## Future / Target State
                    ## Non-Functional Requirements         ### Capabilities
                    ## Objectives & Success Metrics      ## Delta Analysis (Current → Target)
                    ## Open Questions                    ## Migration Strategy
                    ...                                  ## Constraints
                                                           ### Compatibility
                                                           ### Data
                                                         ## Non-Functional Requirements
                                                         ...

                    + raw Q&A transcript saved           + raw Q&A transcript saved
                      to snapshot for audit                to snapshot for audit

CAPABILITIES        Simple L0/L1/L2 hierarchy           Capability Assessment Framework:
(Phase 1):          # L0: Domain                        Part 1: Transformation Pillars
                    ## L1: Capability                      (LLM-derived, with missions)
                    - L2: Sub-capability                Part 2: Assessment Tables
                                                          (Current State | Maturity | Future State)
                                                        Part 3: Gap Summary
                                                          (Critical / Major / Incremental gaps)

CAPABILITY_CARDS    Standard format:                    Migration-enriched format:
(Phase 2):          - Description                       - Description
                    - Objective                         - Objective
                    - Personas                          - Personas
                    - Design Considerations             - Current State Assessment
                    - Success Signals                   - Design Considerations
                    - Related L2                        - Success Signals
                                                        + Migration Approach
                                                        + Quick Wins
                                                        + Long-term Investments
                                                        + Legacy Dependencies to Decommission
                                                        + Transition Risks & Mitigations
                                                        - Related L2

ROADMAP             Standard release phases             Migration wave sequencing
(Phase 2):                                              + legacy decommission milestones
                                                        + parallel-run / cutover gates

HITL at Phase 1:    Review PRD + capabilities           Review PRD + capability assessment
                    (approve/reject)                    + EDIT maturity ratings
                                                        (edited version flows to Phase 2)
```

---

## How the Snapshot-as-Input Mechanism Works

```
Phase 1 runs:
  ArtifactGenerator generates CONTEXT_SUMMARY, CORPUS_SUMMARY, PRD, CAPABILITIES
  User reviews -> Possibly EDITS maturity ratings (modernization) -> Approves
  Snapshot created: frozen copies (with edits applied) + SHA-256 hashes

Phase 2 runs:
  PhasedFlowRunner seeds ArtifactGenerator.cache with Phase 1 snapshot
  Generator calls generate_epics() -> internally calls generate_capabilities()
  generate_capabilities() finds CAPABILITIES in cache -> returns user-approved version
  Epics are generated using the APPROVED (possibly edited) capabilities
  Same for all Phase 1 dependencies

Phase 3 runs:
  Cache seeded with Phase 1 + Phase 2 snapshots
  Generator resolves dependencies -> all hit cache
  Only Phase 3 artifacts are actually generated
```

Approach means:
- **Zero changes** to `ArtifactGenerator`'s dependency resolution logic
- **Zero changes** to individual `generate_*()` greenfield paths
- Existing cache mechanism does all the heavy lifting
- User edits flow forward naturally through the cache
- Snapshots are cryptographically verified via SHA-256

---

## HITL Edit Flow (Capability Maturity Override)

```
                      Phase 1 Generation
                            │
                            ▼
              ┌─────────────────────────┐
              │  LLM generates          │
              │  Capability Assessment  │
              │  with maturity ratings  │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  User reviews in UI     │
              │  Sees assessment table: │
              │  ┌─────────┬──────┬───┐ │
              │  │ L2 Cap  │Curr  │Tgt│ │
              │  ├─────────┼──────┼───┤ │
              │  │ Workflow │Lag ▼ │Led│ │  ◄── user changes "Lagging" to "On Par"
              │  │ Source   │Lag   │Led│ │
              │  │ Fulfill  │Lag   │Par│ │  ◄── user changes target "On Par" to "Leading"
              │  └─────────┴──────┴───┘ │
              └────────────┬────────────┘
                           │
                    POST /approve
                    { edited_artifacts:
                      { "capabilities": "...edited md..." } }
                           │
                           ▼
              ┌─────────────────────────┐
              │  PhasedFlowRunner       │
              │  .approve_phase(1,      │
              │    edited_artifacts={    │
              │      "capabilities": …  │
              │    })                    │
              │                         │
              │  1. Replace in cache    │
              │  2. Create snapshot     │
              │  3. SHA-256 of EDITED   │
              └────────────┬────────────┘
                           │
                           ▼
              Phase 2 generation uses
              EDITED capabilities as input
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Phased mode regressions | `phase_mode=False` default; new code in new files; existing endpoints untouched |
| Snapshot tampering | SHA-256 hashing + verification before cache injection |
| Inconsistent Phase 2 vs approved Phase 1 | Cache seeding ensures approved artifacts used verbatim |
| Modernization prompt quality | Template-driven output (Capability_Assessment_Template.md) constrains LLM format |
| User edits break downstream generation | Edited artifacts go through same validation as LLM output before snapshot |
| Maturity ratings not actionable | Gap Summary (Part 3) auto-generated from delta; migration cards reference it |
| SQLite concurrency | WAL mode + connection-per-request |
| capmap.pdf is domain-specific | LLM derives pillars from input docs (not from PDF); PDF only informs the output STRUCTURE |

---

## Testing Strategy

1. **Unit tests** for each new module:
   - `test_questionnaire.py` -- serialization, validation, both flow types
   - `test_phases.py` -- snapshot creation, hash verification, state machine
   - `test_roadmap.py` -- structure validation
   - `test_flows.py` -- mock LLM, full 3-phase flow
   - `test_phase_store.py` -- SQLite CRUD, concurrency

2. **Prompt regression tests** (modernization):
   - Verify `capabilities_modernization_prompt()` output contains all 3 parts
   - Verify `capability_cards_modernization_prompt()` includes migration sections
   - Verify greenfield prompts unchanged

3. **Integration tests**:
   - Full greenfield 3-phase flow with mock LLM
   - Full modernization 3-phase flow with mock LLM (verify capmap structure)
   - HITL edit at Phase 1 -> verify Phase 2 uses edited content
   - Reject + re-generate flow

4. **Regression tests**:
   - Existing CLI with `phase_mode=False` (must pass unchanged)
   - Existing API endpoints `/api/generate`, `/api/generate-selective` (must pass unchanged)

5. **Snapshot integrity tests**:
   - Edit artifacts -> approve -> verify hash matches edited content
   - Tamper with snapshot file -> verify `verify_snapshot()` rejects
