#!/usr/bin/env python3
"""
Unit tests for Context Summary (Phase 1A) functionality.

Tests the Document Context Assessment artifact generation.
"""
import sys
from pathlib import Path

# Add prdgen to path
sys.path.insert(0, str(Path(__file__).parent))

from prdgen.context_summary import (
    parse_context_summary_markdown,
    format_context_summary_for_consumption,
    _extract_list_items,
    _parse_constraints_section,
    _parse_risks_section,
    _parse_source_traceability
)


def test_extract_list_items():
    """Test list item extraction from markdown"""
    print("\n▶ Testing _extract_list_items...")

    lines = [
        "- Item 1",
        "- Item 2",
        "* Item 3",
        "1. Item 4",
        "Not specified in documents",
        "- Real item 5"
    ]

    items = _extract_list_items(lines)

    assert len(items) == 5, f"Expected 5 items, got {len(items)}"
    assert "Item 1" in items
    assert "Item 5" in items
    assert "Not specified in documents" not in items

    print("  ✓ List extraction works correctly")


def test_parse_constraints_section():
    """Test parsing of constraints section"""
    print("\n▶ Testing _parse_constraints_section...")

    lines = [
        "**Technical Constraints:**",
        "- Must support offline mode",
        "- GPU acceleration required",
        "**Business Constraints:**",
        "- Budget limit of $100k",
        "**Assumptions:**",
        "- Users have modern browsers",
        "- None specified"
    ]

    result = _parse_constraints_section(lines)

    assert len(result["technical_constraints"]) == 2
    assert "Must support offline mode" in result["technical_constraints"]
    assert len(result["business_constraints"]) == 1
    assert len(result["assumptions"]) == 1
    assert "None specified" not in result["assumptions"]

    print("  ✓ Constraints parsing works correctly")


def test_parse_risks_section():
    """Test parsing of risks, gaps, and questions section"""
    print("\n▶ Testing _parse_risks_section...")

    lines = [
        "**Risks:**",
        "- Technical complexity high",
        "- Market timing uncertain",
        "**Information Gaps:**",
        "- User personas not defined",
        "**Open Questions:**",
        "- Which cloud provider?",
        "**Conflicts:**",
        "- Doc A says OAuth, Doc B says JWT"
    ]

    result = _parse_risks_section(lines)

    assert len(result["risks"]) == 2
    assert len(result["information_gaps"]) == 1
    assert len(result["open_questions"]) == 1
    assert len(result["conflicts"]) == 1

    print("  ✓ Risks section parsing works correctly")


def test_parse_source_traceability():
    """Test parsing of source traceability section"""
    print("\n▶ Testing _parse_source_traceability...")

    lines = [
        "**Problem/Opportunity:** [file1.docx, file2.md]",
        "**Goals:** [file1.docx]",
        "**Requirements:** [file3.txt, file4.md]"
    ]

    result = _parse_source_traceability(lines)

    assert "problem_opportunity" in result
    assert len(result["problem_opportunity"]) == 2
    assert "file1.docx" in result["problem_opportunity"]
    assert len(result["goals"]) == 1

    print("  ✓ Source traceability parsing works correctly")


def test_parse_context_summary_markdown():
    """Test full markdown parsing"""
    print("\n▶ Testing parse_context_summary_markdown...")

    sample_md = """## Problem / Opportunity
Customers need faster AI deployment with industry-specific solutions.

## Goals
- Accelerate time-to-value
- Reduce configuration errors

## Non-Goals
- Not a generic AI platform

## Target Personas / Users
- Enterprise IT Manager: Responsible for AI deployment
- Data Scientist: Uses the platform for model training

## Key Functional Requirements
- Blueprint installation via UI
- GPU-accelerated inference support

## Constraints & Assumptions
**Technical Constraints:**
- Must support NVIDIA GPUs

**Business Constraints:**
- Initial release Q2 2024

**Assumptions:**
- Customers have enterprise infrastructure

## Risks, Gaps, and Open Questions
**Risks:**
- Technical complexity may delay launch

**Information Gaps:**
- Pricing model not defined

**Open Questions:**
- Cloud vs on-premise first?

**Conflicts:**
- None identified

## Source Traceability
**Problem/Opportunity:** [blueprint_spec.docx]
**Goals:** [blueprint_spec.docx, requirements.md]
"""

    result = parse_context_summary_markdown(sample_md)

    # Check all sections are present
    assert "problem_opportunity" in result
    assert "Customers need faster" in result["problem_opportunity"]

    assert len(result["goals"]) == 2
    assert "Accelerate time-to-value" in result["goals"]

    assert len(result["target_personas"]) == 2
    assert any("IT Manager" in p for p in result["target_personas"])

    assert len(result["key_functional_requirements"]) == 2

    constraints = result["constraints_assumptions"]
    assert len(constraints["technical_constraints"]) == 1
    assert len(constraints["assumptions"]) == 1

    risks = result["risks_gaps_questions"]
    assert len(risks["risks"]) == 1
    assert len(risks["information_gaps"]) == 1

    traceability = result["source_traceability"]
    assert "problem_opportunity" in traceability
    assert "blueprint_spec.docx" in traceability["problem_opportunity"]

    print("  ✓ Full markdown parsing works correctly")
    print(f"    - Extracted {len(result['goals'])} goals")
    print(f"    - Extracted {len(result['target_personas'])} personas")
    print(f"    - Extracted {len(result['key_functional_requirements'])} requirements")


def test_format_for_consumption():
    """Test formatting for consumption by downstream artifacts"""
    print("\n▶ Testing format_context_summary_for_consumption...")

    context_dict = {
        "problem_opportunity": "Need faster AI deployment",
        "goals": ["Accelerate time-to-value", "Reduce errors"],
        "non_goals": ["Not a generic platform"],
        "target_personas": ["IT Manager", "Data Scientist"],
        "key_functional_requirements": ["Blueprint installation", "GPU support"],
        "constraints_assumptions": {
            "technical_constraints": ["NVIDIA GPUs required"],
            "business_constraints": [],
            "assumptions": ["Enterprise infrastructure"]
        },
        "risks_gaps_questions": {
            "risks": ["Complexity may delay"],
            "information_gaps": ["Pricing undefined"],
            "open_questions": ["Cloud vs on-premise?"],
            "conflicts": []
        },
        "source_traceability": {}
    }

    formatted = format_context_summary_for_consumption(context_dict)

    assert "## Document Context Summary" in formatted
    assert "Need faster AI deployment" in formatted
    assert "Accelerate time-to-value" in formatted
    assert "IT Manager" in formatted
    assert "Blueprint installation" in formatted

    print("  ✓ Formatting for consumption works correctly")
    print(f"    - Generated {len(formatted)} character summary")


def test_integration():
    """Integration test with realistic example"""
    print("\n▶ Testing integration scenario...")

    # Simulate a full context summary output
    sample_output = """## Problem / Opportunity
Industry Blueprints address the challenge of rapid AI deployment in regulated environments.
Customers spend months configuring AI solutions. This product reduces time-to-value significantly.

## Goals
- Accelerate customer onboarding through pre-built solutions
- Enable repeatable, scalable delivery of domain expertise
- Position platform as industry-aware, not just workflow-capable

## Non-Goals
- Building a general-purpose AI framework
- Supporting non-NVIDIA hardware in initial release
- Replacing existing customer AI infrastructure

## Target Personas / Users
- Enterprise AI Architect: Designs and deploys AI solutions for regulated industries
- Platform Administrator: Manages installation and lifecycle of blueprints
- Data Scientist: Customizes workflows and models within blueprints

## Key Functional Requirements
- Blueprint packaging with manifest-driven definitions
- Support for private cloud and on-premise deployments
- GPU-accelerated inference with NVIDIA stack
- Pre-loaded domain knowledge with embeddings
- Workflow Designer for post-installation customization

## Constraints & Assumptions
**Technical Constraints:**
- Initial support only for NVIDIA-accelerated environments
- Model artifacts must be compatible with on-prem environments

**Business Constraints:**
- Launch timeline aligned with NVIDIA partnership announcement
- Must maintain consistent pricing across deployment types

**Assumptions:**
- Customers have existing Kubernetes infrastructure
- Regulatory compliance requirements vary by industry
- NVIDIA GPUs are standard in target customer environments

## Risks, Gaps, and Open Questions
**Risks:**
- Technical complexity of multi-model orchestration may delay launch
- Customer adoption dependent on NVIDIA hardware availability
- Competition from cloud-native solutions

**Information Gaps:**
- Specific pricing model for blueprint marketplace not defined
- Support and maintenance SLAs for blueprints unclear
- Migration path from pilot to production not documented

**Open Questions:**
- Which industries should be prioritized for initial blueprints?
- How to handle conflicts between blueprint versions?
- What level of customization invalidates support agreements?

**Conflicts:**
- Document A specifies Q2 launch, Document B indicates Q3 beta

## Source Traceability
**Problem/Opportunity:** [Industry Blueprint _V1.docx]
**Goals:** [Industry Blueprint _V1.docx]
**Personas:** [Industry Blueprint _V1.docx, stakeholder_interviews.md]
**Requirements:** [Industry Blueprint _V1.docx]
**Constraints:** [Industry Blueprint _V1.docx, partnership_agreement.pdf]
"""

    # Parse it
    parsed = parse_context_summary_markdown(sample_output)

    # Verify comprehensive extraction
    assert parsed["problem_opportunity"], "Problem/Opportunity should not be empty"
    assert len(parsed["goals"]) >= 3, f"Expected at least 3 goals, got {len(parsed['goals'])}"
    assert len(parsed["non_goals"]) >= 2, f"Expected at least 2 non-goals, got {len(parsed['non_goals'])}"
    assert len(parsed["target_personas"]) >= 3, f"Expected at least 3 personas"
    assert len(parsed["key_functional_requirements"]) >= 3, "Should have multiple requirements"

    # Check nested structures
    assert len(parsed["constraints_assumptions"]["technical_constraints"]) >= 2
    assert len(parsed["constraints_assumptions"]["assumptions"]) >= 2
    assert len(parsed["risks_gaps_questions"]["risks"]) >= 2
    assert len(parsed["risks_gaps_questions"]["information_gaps"]) >= 2
    assert len(parsed["risks_gaps_questions"]["open_questions"]) >= 2
    assert len(parsed["risks_gaps_questions"]["conflicts"]) >= 1

    # Check source traceability
    assert "problem_opportunity" in parsed["source_traceability"]
    assert len(parsed["source_traceability"]["problem_opportunity"]) >= 1

    # Test consumption format
    consumable = format_context_summary_for_consumption(parsed)
    assert len(consumable) > 500, "Consumable format should be substantial"
    assert "Industry Blueprints" in consumable

    print("  ✓ Integration test passed")
    print(f"\n  Summary Statistics:")
    print(f"    - Goals: {len(parsed['goals'])}")
    print(f"    - Non-Goals: {len(parsed['non_goals'])}")
    print(f"    - Personas: {len(parsed['target_personas'])}")
    print(f"    - Requirements: {len(parsed['key_functional_requirements'])}")
    print(f"    - Technical Constraints: {len(parsed['constraints_assumptions']['technical_constraints'])}")
    print(f"    - Risks: {len(parsed['risks_gaps_questions']['risks'])}")
    print(f"    - Open Questions: {len(parsed['risks_gaps_questions']['open_questions'])}")
    print(f"    - Source Files: {len(parsed['source_traceability'])}")


if __name__ == "__main__":
    print("=" * 70)
    print("CONTEXT SUMMARY (PHASE 1A) TEST SUITE")
    print("=" * 70)

    try:
        test_extract_list_items()
        test_parse_constraints_section()
        test_parse_risks_section()
        test_parse_source_traceability()
        test_parse_context_summary_markdown()
        test_format_for_consumption()
        test_integration()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nPhase 1A implementation verified:")
        print("  ✓ Context summary parsing")
        print("  ✓ JSON conversion")
        print("  ✓ Source traceability")
        print("  ✓ Consumption formatting")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
