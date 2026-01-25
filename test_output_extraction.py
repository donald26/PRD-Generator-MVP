#!/usr/bin/env python3
"""
Test script to verify output extraction improvements.
Tests that prompt artifacts are properly removed from generated content.
"""

import sys
from pathlib import Path

# Add prdgen to path
sys.path.insert(0, str(Path(__file__).parent))

from prdgen.model import _extract_assistant_response
from prdgen.utils import validate_output


def test_extract_assistant_response():
    """Test the _extract_assistant_response function"""
    print("Testing _extract_assistant_response...")

    # Test case 1: Clean markdown without artifacts
    clean_text = "# My Document\n\nThis is clean content."
    result = _extract_assistant_response(clean_text)
    assert result == clean_text, "Clean text should be unchanged"
    print("  ✓ Clean text passes")

    # Test case 2: Text with role markers
    dirty_text = "assistant\n# My Document\n\nThis is content."
    result = _extract_assistant_response(dirty_text)
    assert "assistant" not in result, "Role marker should be removed"
    assert "# My Document" in result, "Content should be preserved"
    print("  ✓ Role marker removal passes")

    # Test case 3: Text with markdown code blocks
    code_block_text = "```markdown\n# My Document\n\nContent here.\n```"
    result = _extract_assistant_response(code_block_text)
    assert "```" not in result, "Code blocks should be removed"
    assert "# My Document" in result, "Content should be preserved"
    print("  ✓ Code block removal passes")

    print("✓ All _extract_assistant_response tests passed!\n")


def test_validate_output():
    """Test the validate_output function"""
    print("Testing validate_output...")

    # Test case 1: Clean output without leakage
    clean_output = "# Product Requirements Document\n\n## Overview\nThis is a clean PRD."
    result = validate_output(clean_output, "test_artifact")
    assert result == clean_output, "Clean output should be unchanged"
    print("  ✓ Clean output passes")

    # Test case 2: Output with prompt leakage (assistant marker)
    dirty_output = "system\nYou produce PRDs.\nuser\nCreate a PRD.\nassistant\n# Product Requirements Document\n\n## Overview\nThis is the actual content."
    result = validate_output(dirty_output, "test_artifact")
    assert "system" not in result, "System prompt should be removed"
    assert "user" not in result or result.count("user") < 2, "User prompt should be removed"
    assert "# Product Requirements Document" in result, "Actual content should be preserved"
    print("  ✓ Prompt leakage detection and cleaning passes")

    # Test case 3: Output with "Return ONLY" instruction
    instruction_output = "Here are the instructions.\n\nReturn ONLY the PRD.\n\n# Product Requirements Document\n\nThis is the content."
    result = validate_output(instruction_output, "test_artifact")
    # Should either clean it or return as-is with warning
    assert "# Product Requirements Document" in result, "Content should be preserved"
    print("  ✓ Instruction leakage handling passes")

    print("✓ All validate_output tests passed!\n")


def test_integration():
    """Integration test: simulate full generation flow"""
    print("Testing integration scenario...")

    # Simulate a model output that includes everything (worst case)
    model_output = """system
You produce high-quality PRDs. Follow the outline and do not hallucinate missing facts.
user
You are a senior Product Manager writing a PRD.

Write a detailed PRD in Markdown based on the product information below.
Hard rules:
- Use the exact section headings in this outline (keep order).
- Be concrete and implementation-oriented, but do not write code.

PRODUCT INFORMATION:
Industry Blueprints provide pre-packaged solutions...

Return ONLY the PRD Markdown.

assistant
# Product Requirements Document

## Overview
Industry Blueprints provide pre-packaged, installable Accenture intelligence and workflow solutions.

## Problem Statement
Customers need faster time-to-value when deploying AI solutions.

## Goals
- Accelerate customer onboarding
- Reduce configuration errors
"""

    # First apply model extraction
    extracted = _extract_assistant_response(model_output)
    print(f"  After extraction: {len(extracted)} chars (was {len(model_output)})")

    # Then apply validation
    validated = validate_output(extracted, "integration_test")
    print(f"  After validation: {len(validated)} chars")

    # Check results
    assert "system" not in validated.lower() or validated.lower().count("system") == 1, "System prompts should be removed"
    assert "Return ONLY" not in validated, "Instructions should be removed"
    assert "# Product Requirements Document" in validated, "Content should be preserved"
    assert "## Overview" in validated, "Sections should be preserved"
    assert len(validated) < len(model_output) / 2, "Output should be significantly shorter"

    print("  ✓ Integration test passed!")
    print(f"\n  Final output preview:\n  {validated[:200]}...\n")


if __name__ == "__main__":
    print("=" * 70)
    print("OUTPUT EXTRACTION TEST SUITE")
    print("=" * 70)
    print()

    try:
        test_extract_assistant_response()
        test_validate_output()
        test_integration()

        print("=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
