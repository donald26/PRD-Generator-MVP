# Two-Step Intelligent PRD Generation Workflow

## Overview

The PRD Generator now implements an intelligent two-step workflow that analyzes your input documents and automatically recommends which artifacts to generate based on the content.

## Workflow Steps

### Step 1: Document Context Assessment

**What it does:**
- Analyzes all input documents to extract structured context
- Produces `context_summary.md` with standardized sections
- Generates `context_summary.json` for programmatic access

**Output Structure:**
- **Problem / Opportunity**: Core business problem or opportunity
- **Goals / Non-Goals**: What's in scope and explicitly out of scope
- **Target Personas / Users**: User types and stakeholders
- **Key Functional Requirements**: High-level capabilities needed
- **Constraints & Assumptions**: Technical, business, and assumed constraints
- **Risks, Gaps, and Open Questions**: Identified issues and unknowns
- **Source Traceability**: Which files contributed to which sections

**Example:**
```markdown
## Problem / Opportunity
Need to build e-commerce platform for online retail market...

## Goals
- Launch MVP in 6 months
- Support 100K concurrent users
- Integrate with 3 payment gateways
...

## Key Functional Requirements
- User registration and authentication
- Product catalog with search and filtering
- Shopping cart with real-time pricing
...
```

### Step 2: Intelligent Artifact Recommendation

**What it does:**
- Analyzes the context summary to understand project characteristics
- Evaluates project complexity, scope, and focus area
- Recommends which artifacts make sense for your project
- Produces `recommendation.json` with confidence scores and rationale

**Recommendation Criteria:**

| Artifact | Recommended When |
|----------|-----------------|
| **PRD** | Almost always (foundation document) |
| **Capabilities** | ≥5 functional requirements identified |
| **Capability Cards** | ≥8 requirements (complex projects) |
| **Epics** | ≥3 goals OR ≥5 requirements (larger initiatives) |
| **Features** | ≥3 requirements + personas defined |
| **User Stories** | ≥5 requirements + personas + technical detail |
| **Lean Canvas** | Business-focused project with clear problem statement |

**Confidence Levels:**
- **High (≥80%)**: Strongly recommended for your project
- **Medium (50-79%)**: Could be useful but not critical
- **Low (<50%)**: May add unnecessary overhead

**Example `recommendation.json`:**
```json
{
  "recommendations": [
    {
      "artifact_type": "prd",
      "confidence": 95,
      "rationale": "Strong foundation: clear problem and goals defined",
      "recommended": true
    },
    {
      "artifact_type": "capabilities",
      "confidence": 90,
      "rationale": "Rich functional requirements (12 identified) justify capability mapping",
      "recommended": true
    },
    {
      "artifact_type": "user_stories",
      "confidence": 45,
      "rationale": "Some requirements but may lack detail for actionable user stories",
      "recommended": false
    }
  ],
  "summary": {
    "total_artifacts": 7,
    "recommended": 5,
    "high_confidence": 5,
    "medium_confidence": 0,
    "low_confidence": 2
  }
}
```

## Configuration Options

### 1. Automatic Mode (Default)
Let the system analyze and recommend:
```python
cfg = GenerationConfig(
    enable_context_summary=True,    # Generate context assessment
    enable_recommendation=True,      # Use intelligent recommendations
    # ... other config
)
```

### 2. User Override Mode
Explicitly specify which artifacts to generate:
```python
cfg = GenerationConfig(
    enable_context_summary=True,
    enable_recommendation=False,     # Skip recommendation
    generate_only={"prd", "epics"},  # Only generate these
)
```

### 3. Traditional Mode
Use predefined artifact sets:
```python
cfg = GenerationConfig(
    enable_context_summary=False,    # Skip context assessment
    enable_recommendation=False,     # Skip recommendation
    default_set="development",        # Use predefined set
    # Options: "minimal", "business", "development", "complete"
)
```

### 4. Hybrid Mode
Get recommendations but override selectively:
```python
cfg = GenerationConfig(
    enable_context_summary=True,
    enable_recommendation=True,       # Get recommendations
    generate_only={"prd", "features"} # But override with these
)
```

## Priority Order

The system follows this priority order:

1. **User Override** (`generate_only`) - Highest priority
   - If set, these artifacts are generated regardless of recommendations

2. **Intelligent Recommendation** (`enable_recommendation=True`)
   - If enabled and context summary available, uses AI recommendations

3. **Explicit Selection** (`selected_artifacts`)
   - If set, uses these specific artifacts

4. **Default Set** (`default_set`)
   - Falls back to predefined set ("business", "minimal", "development", "complete")

## Example Use Cases

### Use Case 1: New Project (Automatic Mode)
```python
# Let the system analyze and recommend
cfg = GenerationConfig(
    enable_context_summary=True,
    enable_recommendation=True,
    output_dir="./output"
)

# System will:
# 1. Analyze documents → context_summary.md
# 2. Generate recommendations → recommendation.json
# 3. Generate recommended artifacts
```

### Use Case 2: Quick PRD Only
```python
# Override to generate just PRD quickly
cfg = GenerationConfig(
    enable_context_summary=True,     # Still get context
    generate_only={"prd"}             # But only generate PRD
)
```

### Use Case 3: Development-Ready Project
```python
# Generate everything needed for development
cfg = GenerationConfig(
    enable_context_summary=True,
    enable_recommendation=True,       # Get smart recommendations
    # System will likely recommend:
    # - PRD, Capabilities, Epics, Features, User Stories
)
```

### Use Case 4: Business Planning
```python
# For business/strategic focus
cfg = GenerationConfig(
    enable_context_summary=True,
    enable_recommendation=True,
    # System will likely recommend:
    # - PRD, Capabilities, Lean Canvas
)
```

## Benefits

### 1. Intelligent Adaptation
- **Small Projects**: System recommends only essential artifacts (PRD, maybe Features)
- **Large Projects**: Recommends full breakdown (PRD, Capabilities, Epics, Features, Stories)
- **Business Focus**: Adds Lean Canvas for strategic planning
- **Technical Focus**: Emphasizes Features and User Stories for development

### 2. Transparency
- Every recommendation includes:
  - Confidence score (0-100)
  - Clear rationale explaining the recommendation
  - Recommended flag (true/false)

### 3. Flexibility
- Accept recommendations automatically
- Override with `generate_only` when you know what you need
- Mix and match (get recommendations, then override specific ones)

### 4. Traceability
- Context summary shows which input files contributed to each section
- Recommendation rationale explains why each artifact was recommended

## Output Files

After running the two-step workflow, you'll find:

```
output/
├── context_summary.md          # Step 1: Structured document analysis
├── context_summary.json        # Step 1: JSON format
├── recommendation.json         # Step 2: Artifact recommendations
├── prd.md                      # Generated artifacts...
├── capabilities.md
├── epics.md
├── features.md
└── run.json                    # Generation metadata
```

## API Example

```python
from prdgen.config import GenerationConfig
from prdgen.model import load_llama
from prdgen.ingest import ingest_folder
from prdgen.generator import generate_artifacts_selective

# Load model
model = load_llama("Qwen/Qwen2.5-1.5B-Instruct")

# Configure with two-step workflow
cfg = GenerationConfig(
    enable_context_summary=True,      # Step 1: Context assessment
    enable_recommendation=True,        # Step 2: Smart recommendations
    output_dir="./output",
    save_incremental=True,
    use_cache=True
)

# Ingest documents
docs = ingest_folder("./input", include_exts=[".txt", ".md", ".docx"])

# Generate with intelligent recommendations
artifacts, metadata = generate_artifacts_selective(model, cfg, docs)

# Check what was recommended
print(f"Artifacts generated: {list(artifacts.keys())}")
print(f"Based on: {metadata['artifact_selection']}")  # "recommendation"
```

## Disabling the Two-Step Workflow

If you prefer the traditional approach:

```python
cfg = GenerationConfig(
    enable_context_summary=False,     # Skip context assessment
    enable_recommendation=False,      # Skip recommendations
    default_set="complete"            # Generate all artifacts
)
```

## FAQ

**Q: Does this slow down generation?**
A: Context assessment adds one quick analysis step (~5-10 seconds). The recommendation is instant (rule-based analysis). Overall impact is minimal compared to time saved by not generating unnecessary artifacts.

**Q: Can I see recommendations without generating artifacts?**
A: Yes! Run with `enable_recommendation=True` and `generate_only=set()` (empty set). You'll get `recommendation.json` without generating other artifacts.

**Q: What if I disagree with the recommendations?**
A: Use `generate_only` to override. The system respects explicit user intent.

**Q: Are recommendations based on AI?**
A: No, recommendations use rule-based analysis of the context summary. This makes them fast, predictable, and explainable.

**Q: Can I customize recommendation logic?**
A: Yes! Edit `prdgen/recommendation.py` to adjust confidence thresholds or add custom rules for your organization.

## Conclusion

The two-step workflow makes PRD generation smarter by:
1. Understanding your project context first
2. Recommending appropriate artifacts based on that understanding
3. Giving you full control to accept or override recommendations
4. Providing transparency through confidence scores and rationale

Start with automatic mode and adjust based on your needs!
