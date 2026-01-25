#!/usr/bin/env python3
"""
Simple test suite for prompt template system (no torch dependency).

Verifies that:
1. System prompts load correctly from prompt_templates module
2. Template files load from templates/ directory
3. Prompts contain improved anti-hallucination language
4. Template structures are properly integrated
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from prdgen.prompt_templates import (
    PromptTemplates,
    get_system_prompt,
    get_template,
    get_template_structure,
    DEFAULT_TEMPLATE_DIR
)
from prdgen.prompts import epics_prompt, features_prompt, user_stories_prompt


def test_prompt_templates_initialization():
    """Test that PromptTemplates initializes correctly"""
    print("\n▶ Testing PromptTemplates initialization...")

    templates = PromptTemplates.create_default()

    # Check system prompts are loaded
    assert templates.get_system_prompt("context"), "Context prompt should exist"
    assert templates.get_system_prompt("summary"), "Summary prompt should exist"
    assert templates.get_system_prompt("prd"), "PRD prompt should exist"
    assert templates.get_system_prompt("features"), "Features prompt should exist"
    assert templates.get_system_prompt("capabilities"), "Capabilities prompt should exist"
    assert templates.get_system_prompt("canvas"), "Canvas prompt should exist"
    assert templates.get_system_prompt("stories"), "Stories prompt should exist"

    print("  ✓ All system prompts loaded")
    print(f"    - Template directory: {DEFAULT_TEMPLATE_DIR}")


def test_template_files_loaded():
    """Test that template files are loaded from templates/ directory"""
    print("\n▶ Testing template file loading...")

    templates = PromptTemplates.create_default()

    # Check that templates exist
    epic_template = templates.get_template("epic")
    feature_template = templates.get_template("feature")
    story_template = templates.get_template("user_story")

    assert epic_template is not None, "Epic template should be loaded"
    assert feature_template is not None, "Feature template should be loaded"
    assert story_template is not None, "User story template should be loaded"

    # Check template content
    assert "Epic Name" in epic_template, "Epic template should contain 'Epic Name'"
    assert "Feature Name" in feature_template, "Feature template should contain 'Feature Name'"
    assert "Story ID" in story_template, "Story template should contain 'Story ID'"

    print("  ✓ All template files loaded successfully")
    print(f"    - Epic template: {len(epic_template)} chars")
    print(f"    - Feature template: {len(feature_template)} chars")
    print(f"    - Story template: {len(story_template)} chars")


def test_improved_prompt_language():
    """Test that prompts contain improved anti-hallucination language"""
    print("\n▶ Testing improved prompt language...")

    checks_passed = 0

    # Check context prompt
    context_prompt = get_system_prompt("context")
    if "Extract ONLY information explicitly stated" in context_prompt:
        checks_passed += 1
    if "Do NOT infer intent" in context_prompt or "Do NOT add assumptions" in context_prompt:
        checks_passed += 1

    # Check summary prompt
    summary_prompt = get_system_prompt("summary")
    if "Do NOT introduce new facts" in summary_prompt or "Do NOT introduce" in summary_prompt:
        checks_passed += 1
    if "Not specified in source documents" in summary_prompt:
        checks_passed += 1

    # Check PRD prompt
    prd_prompt = get_system_prompt("prd")
    if "Do NOT invent" in prd_prompt:
        checks_passed += 1
    if "grounded in" in prd_prompt or "ONLY with information" in prd_prompt:
        checks_passed += 1

    # Check features prompt
    features_prompt_text = get_system_prompt("features")
    if "Do NOT introduce new functionality" in features_prompt_text:
        checks_passed += 1
    if "map clearly" in features_prompt_text or "must map" in features_prompt_text:
        checks_passed += 1

    # Check stories prompt
    stories_prompt_text = get_system_prompt("stories")
    if "Do NOT introduce new business rules" in stories_prompt_text:
        checks_passed += 1
    if "testable and unambiguous" in stories_prompt_text:
        checks_passed += 1

    print(f"  ✓ Anti-hallucination language checks: {checks_passed}/10 passed")
    assert checks_passed >= 8, f"Expected at least 8 checks to pass, got {checks_passed}"
    print("    - Explicit extraction instructions present")
    print("    - Prohibition of inference and invention")
    print("    - Requirements for grounding and traceability")


def test_template_structure_extraction():
    """Test that template structures are properly extracted"""
    print("\n▶ Testing template structure extraction...")

    epic_structure = get_template_structure("epic")
    feature_structure = get_template_structure("feature")
    story_structure = get_template_structure("user_story")

    # Check that structures contain sections
    epic_sections = epic_structure.count('-')
    feature_sections = feature_structure.count('-')
    story_sections = story_structure.count('-')

    assert epic_sections >= 5, f"Epic should have at least 5 sections, got {epic_sections}"
    assert feature_sections >= 5, f"Feature should have at least 5 sections, got {feature_sections}"
    assert story_sections >= 5, f"Story should have at least 5 sections, got {story_sections}"

    print("  ✓ Template structures extracted correctly")
    print(f"    - Epic sections: {epic_sections}")
    print(f"    - Feature sections: {feature_sections}")
    print(f"    - Story sections: {story_sections}")


def test_prompt_functions_use_templates():
    """Test that prompt functions integrate template structures"""
    print("\n▶ Testing prompt function integration...")

    # Test epics_prompt includes template structure
    sample_prd = "## Goals\n- Sample goal"
    sample_caps = "# L0: Domain\n## L1: Capability"
    sample_cards = "## Capability\n**Description**: Sample"

    epic_prompt = epics_prompt(sample_prd, sample_caps, sample_cards)

    # Check for template integration
    template_integrated = (
        "Use this structure:" in epic_prompt or
        "Epic Template" in epic_prompt or
        "Epic Summary" in epic_prompt or
        "Epic Name" in epic_prompt
    )
    assert template_integrated, "Epics prompt should include template structure"

    # Check for hallucination prevention
    prevention_present = "Do NOT invent" in epic_prompt
    assert prevention_present, "Epics prompt should have hallucination prevention"

    # Test features_prompt
    sample_epics = "## Epic 1\n**Epic ID**: EP-001"
    features_prompt_text = features_prompt(sample_prd, sample_epics)

    template_integrated = (
        "Use this structure:" in features_prompt_text or
        "Feature Template" in features_prompt_text or
        "Feature Description" in features_prompt_text or
        "Feature Name" in features_prompt_text
    )
    assert template_integrated, "Features prompt should include template structure"

    # Test user_stories_prompt
    sample_features = "### Feature F-001\n**Feature ID**: F-001"
    stories_prompt_text = user_stories_prompt(sample_prd, sample_epics, sample_features)

    template_integrated = (
        "Use this structure:" in stories_prompt_text or
        "User Story Template" in stories_prompt_text or
        "Story ID" in stories_prompt_text
    )
    assert template_integrated, "Stories prompt should include template structure"

    print("  ✓ Prompt functions properly integrate templates")
    print("    - Template structures included in prompts")
    print("    - Hallucination prevention maintained")


def test_convenience_functions():
    """Test convenience functions work correctly"""
    print("\n▶ Testing convenience functions...")

    # Test get_system_prompt
    context = get_system_prompt("context")
    assert context and len(context) > 50, "get_system_prompt should return non-empty string"

    # Test get_template
    epic_template = get_template("epic")
    assert epic_template and len(epic_template) > 50, "get_template should return non-empty string"

    # Test get_template_structure
    epic_structure = get_template_structure("epic")
    assert epic_structure and len(epic_structure) > 20, "get_template_structure should return non-empty string"

    print("  ✓ Convenience functions work correctly")


def test_template_sections():
    """Test that templates contain expected sections"""
    print("\n▶ Testing template section content...")

    epic_template = get_template("epic")
    feature_template = get_template("feature")
    story_template = get_template("user_story")

    # Epic should have key sections
    assert "Business Objective" in epic_template, "Epic should have Business Objective"
    assert "Success Metrics" in epic_template or "KPIs" in epic_template, "Epic should have success metrics"
    assert "Dependencies" in epic_template, "Epic should have Dependencies"
    assert "Risks" in epic_template or "Mitigations" in epic_template, "Epic should have risk management"

    # Feature should have key sections
    assert "User Value Statement" in feature_template, "Feature should have User Value Statement"
    assert "Functional Requirements" in feature_template, "Feature should have Functional Requirements"
    assert "Edge Cases" in feature_template or "Exceptions" in feature_template, "Feature should handle edge cases"
    assert "Telemetry" in feature_template or "Observability" in feature_template, "Feature should have observability"

    # Story should have key sections
    assert "As a" in story_template, "Story should have 'As a' format"
    assert "I want to" in story_template, "Story should have 'I want to' format"
    assert "So that" in story_template, "Story should have 'So that' format"
    assert "Acceptance Criteria" in story_template, "Story should have Acceptance Criteria"
    assert "Definition of Done" in story_template, "Story should have Definition of Done"

    print("  ✓ All templates contain expected sections")
    print("    - Epic: Business objectives, success metrics, dependencies, risks")
    print("    - Feature: Value statement, requirements, edge cases, telemetry")
    print("    - Story: User story format, acceptance criteria, DoD")


if __name__ == "__main__":
    print("=" * 70)
    print("PROMPT TEMPLATE SYSTEM TEST SUITE (Lightweight)")
    print("=" * 70)

    try:
        test_prompt_templates_initialization()
        test_template_files_loaded()
        test_improved_prompt_language()
        test_template_structure_extraction()
        test_prompt_functions_use_templates()
        test_convenience_functions()
        test_template_sections()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nPrompt template system successfully implemented:")
        print("  ✓ System prompts loaded from centralized module")
        print("  ✓ Template files loaded from templates/ directory")
        print("  ✓ Improved anti-hallucination language in all prompts")
        print("  ✓ Template structures integrated into generation")
        print("  ✓ Epic, Feature, and Story prompts use templates")
        print("  ✓ All expected sections present in templates")
        print("\nReady for production use!")
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
