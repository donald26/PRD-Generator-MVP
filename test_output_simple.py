#!/usr/bin/env python3
"""
Simple standalone test for output extraction logic.
No dependencies on torch or other heavy libraries.
"""

import re


def _extract_assistant_response(text: str) -> str:
    """
    Extract only the assistant's response, removing any chat template artifacts.
    (Copied from model.py for standalone testing)
    """
    # Remove common chat template markers at the start
    patterns_to_remove = [
        r"^system\s*\n",
        r"^user\s*\n",
        r"^assistant\s*\n",
        r"^SYSTEM:.*?(?=\n\n)",
        r"^USER:.*?(?=\n\n)",
        r"^ASSISTANT:\s*",
    ]

    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE | re.DOTALL)

    # If text contains markdown code blocks, extract the content
    if cleaned.strip().startswith("```markdown\n"):
        cleaned = re.sub(r"^```markdown\n", "", cleaned.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)
    elif cleaned.strip().startswith("```\n"):
        cleaned = re.sub(r"^```\n", "", cleaned.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)

    return cleaned.strip()


def validate_output(content: str, artifact_name: str) -> str:
    """
    Validate and clean output to ensure no prompt leakage.
    (Copied from utils.py for standalone testing)
    """
    original_length = len(content)

    # Check for common prompt artifacts that indicate leakage
    prompt_indicators = [
        "system\nYou produce",
        "user\nYou are",
        "assistant\n",
        "SYSTEM:",
        "USER:",
        "ASSISTANT:",
        "Return ONLY the",
    ]

    has_leakage = any(indicator in content for indicator in prompt_indicators)

    if has_leakage:
        print(f"  ⚠ {artifact_name}: Detected prompt leakage, cleaning...")

        # Try to extract just the final assistant response
        if "assistant\n" in content:
            parts = content.split("assistant\n")
            cleaned = parts[-1].strip()
            print(f"  ✓ {artifact_name}: Cleaned from {original_length} to {len(cleaned)} chars")
            return cleaned

        # Try to find content after the last "Return ONLY" instruction
        if "Return ONLY" in content:
            parts = content.split("Return ONLY")
            if len(parts) > 1:
                remaining = parts[-1]
                match = re.search(r'\n\n(.+)', remaining, re.DOTALL)
                if match:
                    cleaned = match.group(1).strip()
                    print(f"  ✓ {artifact_name}: Cleaned from {original_length} to {len(cleaned)} chars")
                    return cleaned

        print(f"  ⚠ {artifact_name}: Could not fully clean, returning as-is")

    return content


def test_extract_assistant_response():
    """Test the _extract_assistant_response function"""
    print("\n▶ Testing _extract_assistant_response...")

    # Test case 1: Clean markdown
    clean_text = "# My Document\n\nThis is clean content."
    result = _extract_assistant_response(clean_text)
    assert result == clean_text, f"Expected unchanged, got: {result}"
    print("  ✓ Clean text preserved")

    # Test case 2: Text with role markers
    dirty_text = "assistant\n# My Document\n\nThis is content."
    result = _extract_assistant_response(dirty_text)
    assert "assistant" not in result, f"Role marker not removed: {result}"
    assert "# My Document" in result, f"Content not preserved: {result}"
    print("  ✓ Role markers removed")

    # Test case 3: Text with markdown code blocks
    code_block_text = "```markdown\n# My Document\n\nContent here.\n```"
    result = _extract_assistant_response(code_block_text)
    assert "```" not in result, f"Code blocks not removed: {result}"
    assert "# My Document" in result, f"Content not preserved: {result}"
    print("  ✓ Code blocks removed")

    print("✓ _extract_assistant_response tests passed")


def test_validate_output():
    """Test the validate_output function"""
    print("\n▶ Testing validate_output...")

    # Test case 1: Clean output
    clean_output = "# PRD\n\n## Overview\nClean content."
    result = validate_output(clean_output, "clean_test")
    assert result == clean_output, f"Clean output changed unexpectedly"
    print("  ✓ Clean output preserved")

    # Test case 2: Output with assistant marker
    dirty_output = "system\nPrompt.\nassistant\n# PRD\n\n## Overview\nActual content."
    result = validate_output(dirty_output, "dirty_test")
    assert "system" not in result, f"System prompt not removed"
    assert "# PRD" in result, f"Content not preserved"
    print("  ✓ Prompt leakage cleaned")

    print("✓ validate_output tests passed")


def test_integration():
    """Integration test with realistic example"""
    print("\n▶ Testing integration scenario...")

    # Simulate output from the file you showed me
    model_output = """system
You produce capability maps derived strictly from the PRD.
user
You are a Product Architect. Create a clean set of L1 Capability Cards.

L1 CAPABILITIES (EXACT NAMES):
- Industry Blueprints
- NVIDIA Stack

Return ONLY the capability cards Markdown, with this structure:

## <L1 Capability Name>
**Description**
- ...

assistant
## Industry Blueprints

**Description**
- Deployable, versioned packages of workflows, models, and knowledge artifacts.

**Objective**
- Accelerate customer onboarding through pre-built solutions
"""

    print(f"  Input size: {len(model_output)} chars")

    # Apply extraction
    extracted = _extract_assistant_response(model_output)
    print(f"  After extraction: {len(extracted)} chars")

    # Apply validation
    validated = validate_output(extracted, "integration_test")
    print(f"  After validation: {len(validated)} chars")

    # Verify results
    assert "system" not in validated or validated.count("system") <= 1, "System prompts should be mostly removed"
    assert "Return ONLY" not in validated, "Instructions should be removed"
    assert "## Industry Blueprints" in validated, "Content should be preserved"
    assert "**Description**" in validated, "Structure should be preserved"
    assert len(validated) < len(model_output) / 2, f"Output should be shorter: {len(validated)} vs {len(model_output)}"

    print("\n  Final output preview:")
    print("  " + "-" * 60)
    for line in validated.split("\n")[:10]:
        print(f"  {line}")
    print("  " + "-" * 60)

    print("✓ Integration test passed")


if __name__ == "__main__":
    print("=" * 70)
    print("OUTPUT EXTRACTION VERIFICATION")
    print("=" * 70)

    try:
        test_extract_assistant_response()
        test_validate_output()
        test_integration()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED - Output extraction is working correctly!")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
