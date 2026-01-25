#!/usr/bin/env python3
"""
Simple functional test for Context Summary (Phase 1A).
Verifies basic integration and core parsing functionality.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from prdgen.context_summary import parse_context_summary_markdown, format_context_summary_for_consumption
from prdgen.artifact_types import ArtifactType, ARTIFACT_FILENAMES
from prdgen.dependencies import ArtifactDependencyResolver
from prdgen.config import GenerationConfig


def test_artifact_integration():
    """Test that CONTEXT_SUMMARY is properly integrated"""
    print("\n▶ Testing artifact integration...")

    # Check artifact type exists
    assert hasattr(ArtifactType, 'CONTEXT_SUMMARY')
    assert ArtifactType.CONTEXT_SUMMARY.value == "context_summary"

    # Check filename mapping
    assert ArtifactType.CONTEXT_SUMMARY in ARTIFACT_FILENAMES
    assert ARTIFACT_FILENAMES[ArtifactType.CONTEXT_SUMMARY] == "context_summary.md"

    # Check dependencies
    deps = ArtifactDependencyResolver.DEPENDENCIES[ArtifactType.CONTEXT_SUMMARY]
    assert deps == [], f"CONTEXT_SUMMARY should have no dependencies, got {deps}"

    # Check generation order (should be first)
    first_artifact = ArtifactDependencyResolver.GENERATION_ORDER[0]
    assert first_artifact == ArtifactType.CONTEXT_SUMMARY, f"CONTEXT_SUMMARY should be first, got {first_artifact}"

    print("  ✓ Artifact properly integrated into type system")
    print(f"    - Enum value: {ArtifactType.CONTEXT_SUMMARY.value}")
    print(f"    - Filename: {ARTIFACT_FILENAMES[ArtifactType.CONTEXT_SUMMARY]}")
    print(f"    - Dependencies: {deps}")
    print(f"    - Generation order position: 1/{len(ArtifactDependencyResolver.GENERATION_ORDER)}")


def test_config_flag():
    """Test that config flag exists"""
    print("\n▶ Testing configuration...")

    cfg = GenerationConfig()
    assert hasattr(cfg, 'enable_context_summary')
    assert hasattr(cfg, 'include_source_traceability')
    assert cfg.enable_context_summary == True, "Should be enabled by default"

    print("  ✓ Configuration flags present")
    print(f"    - enable_context_summary: {cfg.enable_context_summary}")
    print(f"    - include_source_traceability: {cfg.include_source_traceability}")


def test_markdown_parsing():
    """Test basic markdown parsing"""
    print("\n▶ Testing markdown parsing...")

    sample_md = """## Problem / Opportunity
We need faster deployment of AI solutions.

## Goals
- Accelerate time-to-value
- Reduce configuration errors

## Non-Goals
- Not a generic AI platform

## Target Personas / Users
- IT Manager: Manages deployments
- Data Scientist: Uses the platform

## Key Functional Requirements
- Blueprint installation via UI
- GPU-accelerated inference

## Constraints & Assumptions
**Technical Constraints:**
- Must support NVIDIA GPUs

**Business Constraints:**
- Q2 2024 release

**Assumptions:**
- Enterprise infrastructure available

## Risks, Gaps, and Open Questions
**Risks:**
- Technical complexity

**Information Gaps:**
- Pricing model undefined

**Open Questions:**
- Cloud vs on-premise?

**Conflicts:**
- None identified

## Source Traceability
**Problem/Opportunity:** [spec.docx]
**Goals:** [spec.docx, req.md]
"""

    result = parse_context_summary_markdown(sample_md)

    # Verify structure
    assert "problem_opportunity" in result
    assert "goals" in result
    assert "target_personas" in result
    assert "key_functional_requirements" in result
    assert "constraints_assumptions" in result
    assert "risks_gaps_questions" in result
    assert "source_traceability" in result

    # Verify content extraction
    assert len(result["goals"]) > 0, "Should extract goals"
    assert len(result["target_personas"]) > 0, "Should extract personas"
    assert len(result["key_functional_requirements"]) > 0, "Should extract requirements"

    print("  ✓ Markdown parsing works")
    print(f"    - Extracted {len(result['goals'])} goals")
    print(f"    - Extracted {len(result['target_personas'])} personas")
    print(f"    - Extracted {len(result['key_functional_requirements'])} requirements")
    print(f"    - Extracted {len(result['source_traceability'])} source mappings")


def test_consumption_format():
    """Test formatting for downstream consumption"""
    print("\n▶ Testing consumption format...")

    context_dict = {
        "problem_opportunity": "Need faster deployment",
        "goals": ["Accelerate", "Reduce errors"],
        "non_goals": ["Not generic"],
        "target_personas": ["IT Manager", "Data Scientist"],
        "key_functional_requirements": ["Blueprint install", "GPU support"],
        "constraints_assumptions": {
            "technical_constraints": ["NVIDIA GPUs"],
            "business_constraints": [],
            "assumptions": ["Enterprise infra"]
        },
        "risks_gaps_questions": {
            "risks": [],
            "information_gaps": [],
            "open_questions": [],
            "conflicts": []
        },
        "source_traceability": {}
    }

    formatted = format_context_summary_for_consumption(context_dict)

    assert "## Document Context Summary" in formatted
    assert "Need faster deployment" in formatted
    assert "Accelerate" in formatted

    print("  ✓ Consumption format generation works")
    print(f"    - Generated {len(formatted)} character summary")


def test_dependency_resolution():
    """Test that CONTEXT_SUMMARY works in dependency resolution"""
    print("\n▶ Testing dependency resolution...")

    # Test selecting just CONTEXT_SUMMARY
    selected = {ArtifactType.CONTEXT_SUMMARY}
    resolved = ArtifactDependencyResolver.resolve(selected)
    assert ArtifactType.CONTEXT_SUMMARY in resolved
    assert len(resolved) == 1

    # Test selecting PRD (should get CORPUS_SUMMARY but not CONTEXT_SUMMARY automatically)
    selected = {ArtifactType.PRD}
    resolved = ArtifactDependencyResolver.resolve(selected)
    # CONTEXT_SUMMARY is independent, so it won't be auto-included
    assert ArtifactType.CORPUS_SUMMARY in resolved
    assert ArtifactType.PRD in resolved

    print("  ✓ Dependency resolution works correctly")
    print(f"    - CONTEXT_SUMMARY: standalone (no deps)")
    print(f"    - PRD dependencies: {[a.value for a in ArtifactDependencyResolver.DEPENDENCIES[ArtifactType.PRD]]}")


if __name__ == "__main__":
    print("=" * 70)
    print("CONTEXT SUMMARY (PHASE 1A) - INTEGRATION TEST")
    print("=" * 70)

    try:
        test_artifact_integration()
        test_config_flag()
        test_markdown_parsing()
        test_consumption_format()
        test_dependency_resolution()

        print("\n" + "=" * 70)
        print("✓ ALL INTEGRATION TESTS PASSED!")
        print("=" * 70)
        print("\nPhase 1A successfully integrated:")
        print("  ✓ New CONTEXT_SUMMARY artifact type")
        print("  ✓ First in generation order (no dependencies)")
        print("  ✓ Configuration flags (enable_context_summary)")
        print("  ✓ Markdown parsing and JSON conversion")
        print("  ✓ Source traceability support")
        print("  ✓ Consumable format for downstream artifacts")
        print("\nReady for generation testing!")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
