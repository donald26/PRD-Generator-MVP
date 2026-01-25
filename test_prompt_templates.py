#!/usr/bin/env python3
"""
Test suite for prompt template system.

Verifies that:
1. System prompts load correctly from prompt_templates module
2. Template files load from templates/ directory
3. Prompts contain improved anti-hallucination language
4. Template structures are properly integrated into generation prompts
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from prdgen.prompt_templates import (
    PromptTemplates,
    get_system_prompt,
    get_template,
    get_template_structure
)
from prdgen.prompts import epics_prompt, features_prompt, user_stories_prompt
from prdgen.generator import (
    SYSTEM_CONTEXT,
    SYSTEM_SUMMARY,
    SYSTEM_PRD,
    SYSTEM_FEATURES,
    SYSTEM_CAPS,
    SYSTEM_CANVAS,
    SYSTEM_STORIES
)


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

    # Check context prompt
    context_prompt = get_system_prompt("context")
    assert "Extract ONLY information explicitly stated" in context_prompt, \
        "Context prompt should have explicit instruction"
    assert "Do NOT infer intent, add assumptions, or fill gaps" in context_prompt, \
        "Context prompt should prohibit inference"

    # Check summary prompt
    summary_prompt = get_system_prompt("summary")
    assert "Do NOT introduce new facts, interpretations, or assumptions" in summary_prompt, \
        "Summary prompt should prohibit hallucination"
    assert "Not specified in source documents" in summary_prompt, \
        "Summary prompt should handle missing info"

    # Check PRD prompt
    prd_prompt = get_system_prompt("prd")
    assert "Do NOT invent requirements" in prd_prompt, \
        "PRD prompt should prohibit invention"
    assert "grounded in the document summary" in prd_prompt, \
        "PRD prompt should require grounding"

    # Check features prompt
    features_prompt_text = get_system_prompt("features")
    assert "Do NOT introduce new functionality not present in the PRD" in features_prompt_text, \
        "Features prompt should limit scope"
    assert "map clearly to a PRD requirement or epic" in features_prompt_text, \
        "Features prompt should require traceability"

    # Check stories prompt
    stories_prompt_text = get_system_prompt("stories")
    assert "Do NOT introduce new business rules" in stories_prompt_text, \
        "Stories prompt should limit scope"
    assert "testable and unambiguous" in stories_prompt_text, \
        "Stories prompt should require clarity"

    print("  ✓ All prompts contain improved anti-hallucination language")
    print("    - Explicit extraction instructions")
    print("    - Prohibition of inference and invention")
    print("    - Requirements for grounding and traceability")


def test_generator_uses_templates():
    """Test that generator module loads system prompts from templates"""
    print("\n▶ Testing generator integration...")

    # Check that constants are loaded from template system
    assert SYSTEM_CONTEXT == get_system_prompt("context"), \
        "Generator should use template context prompt"
    assert SYSTEM_SUMMARY == get_system_prompt("summary"), \
        "Generator should use template summary prompt"
    assert SYSTEM_PRD == get_system_prompt("prd"), \
        "Generator should use template PRD prompt"
    assert SYSTEM_FEATURES == get_system_prompt("features"), \
        "Generator should use template features prompt"
    assert SYSTEM_CAPS == get_system_prompt("capabilities"), \
        "Generator should use template capabilities prompt"
    assert SYSTEM_CANVAS == get_system_prompt("canvas"), \
        "Generator should use template canvas prompt"
    assert SYSTEM_STORIES == get_system_prompt("stories"), \
        "Generator should use template stories prompt"

    print("  ✓ Generator uses prompt templates correctly")


def test_template_structure_extraction():
    """Test that template structures are properly extracted"""
    print("\n▶ Testing template structure extraction...")

    epic_structure = get_template_structure("epic")
    feature_structure = get_template_structure("feature")
    story_structure = get_template_structure("user_story")

    # Epic structure should contain key sections
    assert "Epic Name" in epic_structure or "Epic Summary" in epic_structure, \
        "Epic structure should contain sections"

    # Feature structure should contain key sections
    assert "Feature Name" in feature_structure or "Feature Description" in feature_structure, \
        "Feature structure should contain sections"

    # Story structure should contain key sections
    assert "Story ID" in story_structure or "Title" in story_structure, \
        "Story structure should contain sections"

    print("  ✓ Template structures extracted correctly")
    print(f"    - Epic sections: {epic_structure.count('-')}")
    print(f"    - Feature sections: {feature_structure.count('-')}")
    print(f"    - Story sections: {story_structure.count('-')}")


def test_prompt_functions_use_templates():
    """Test that prompt functions integrate template structures"""
    print("\n▶ Testing prompt function integration...")

    # Test epics_prompt includes template structure
    sample_prd = "## Goals\n- Sample goal"
    sample_caps = "# L0: Domain\n## L1: Capability"
    sample_cards = "## Capability\n**Description**: Sample"

    epic_prompt = epics_prompt(sample_prd, sample_caps, sample_cards)
    assert "Use this structure:" in epic_prompt or "Epic Template" in epic_prompt or "Epic Summary" in epic_prompt, \
        "Epics prompt should include template structure"
    assert "Do NOT invent capabilities" in epic_prompt, \
        "Epics prompt should have hallucination prevention"

    # Test features_prompt includes template structure
    sample_epics = "## Epic 1\n**Epic ID**: EP-001"
    features_prompt_text = features_prompt(sample_prd, sample_epics)
    assert "Use this structure:" in features_prompt_text or "Feature Template" in features_prompt_text or "Feature Description" in features_prompt_text, \
        "Features prompt should include template structure"
    assert "Do NOT invent features" in features_prompt_text, \
        "Features prompt should have hallucination prevention"

    # Test user_stories_prompt includes template structure
    sample_features = "### Feature F-001\n**Feature ID**: F-001"
    stories_prompt_text = user_stories_prompt(sample_prd, sample_epics, sample_features)
    assert "Use this structure:" in stories_prompt_text or "User Story Template" in stories_prompt_text or "Story ID" in stories_prompt_text, \
        "Stories prompt should include template structure"
    assert "Do NOT invent functionality" in stories_prompt_text, \
        "Stories prompt should have hallucination prevention"

    print("  ✓ Prompt functions properly integrate templates")
    print("    - Template structures included")
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


if __name__ == "__main__":
    print("=" * 70)
    print("PROMPT TEMPLATE SYSTEM TEST SUITE")
    print("=" * 70)

    try:
        test_prompt_templates_initialization()
        test_template_files_loaded()
        test_improved_prompt_language()
        test_generator_uses_templates()
        test_template_structure_extraction()
        test_prompt_functions_use_templates()
        test_convenience_functions()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nPrompt template system successfully implemented:")
        print("  ✓ System prompts loaded from centralized module")
        print("  ✓ Template files loaded from templates/ directory")
        print("  ✓ Improved anti-hallucination language in all prompts")
        print("  ✓ Template structures integrated into generation")
        print("  ✓ Generator module uses new template system")
        print("  ✓ Epic, Feature, and Story prompts use templates")
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
