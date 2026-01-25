import re
import logging
from typing import List

LOG = logging.getLogger("prdgen.utils")

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def ensure_sections(markdown: str, headings: List[str]) -> str:
    existing = set(re.findall(r"^##\s+(.+)$", markdown, flags=re.MULTILINE))
    missing = [h for h in headings if h not in existing]
    if not missing:
        return markdown.strip() + "\n"
    out = markdown.strip() + "\n\n"
    out += "\n".join([f"## {h}\n(TBD)\n" for h in missing])
    return out.strip() + "\n"

def strip_trailing_noise(text: str) -> str:
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def validate_output(content: str, artifact_name: str) -> str:
    """
    Validate and clean output to ensure no prompt leakage.

    Checks for common prompt artifacts and attempts to extract clean content.

    Args:
        content: The generated content to validate
        artifact_name: Name of the artifact (for logging)

    Returns:
        Cleaned content
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
        LOG.warning(f"{artifact_name}: Detected potential prompt leakage in output!")

        # Try to extract just the final assistant response
        # Look for the last occurrence of "assistant" marker
        if "assistant\n" in content:
            parts = content.split("assistant\n")
            cleaned = parts[-1].strip()
            LOG.info(f"{artifact_name}: Extracted {len(cleaned)} chars after cleaning (was {original_length})")
            return cleaned

        # Try to find content after the last "Return ONLY" instruction
        if "Return ONLY" in content:
            parts = content.split("Return ONLY")
            # Get everything after the last instruction
            if len(parts) > 1:
                # Find the next substantial content block (likely after a newline)
                remaining = parts[-1]
                match = re.search(r'\n\n(.+)', remaining, re.DOTALL)
                if match:
                    cleaned = match.group(1).strip()
                    LOG.info(f"{artifact_name}: Extracted {len(cleaned)} chars after cleaning (was {original_length})")
                    return cleaned

        # If we couldn't clean it, log a warning but return as-is
        LOG.warning(f"{artifact_name}: Could not fully clean output, returning as-is")

    return content
