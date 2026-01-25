"""
Output format handlers for artifacts.
Supports multiple output formats: Markdown, JSON, HTML.
"""
from typing import Dict
from pathlib import Path
import json
import logging

LOG = logging.getLogger("prdgen.formatters")

def save_artifacts(
    artifacts: Dict[str, str],
    output_dir: Path,
    formats: set = {"markdown"},
    metadata: Dict = None
):
    """
    Save artifacts in specified formats.

    Args:
        artifacts: Dict of artifact_name -> markdown content
        output_dir: Where to save
        formats: Set of format names ("markdown", "json", "html")
        metadata: Optional metadata to include in structured formats
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if "markdown" in formats:
        # Save individual markdown files (default)
        for name, content in artifacts.items():
            filename = f"{name}.md" if not name.endswith('.md') else name
            (output_dir / filename).write_text(content, encoding='utf-8')
            LOG.info(f"Saved markdown: {filename}")

    if "json" in formats:
        # Save structured JSON
        from .json_formatter import JSONFormatter
        json_formatter = JSONFormatter()
        json_output = json_formatter.format_all(artifacts, metadata)
        (output_dir / "artifacts.json").write_text(json_output, encoding='utf-8')
        LOG.info("Saved JSON: artifacts.json")

    if "html" in formats:
        # Save HTML report
        from .html_formatter import HTMLFormatter
        html_formatter = HTMLFormatter()
        html_output = html_formatter.generate_report(artifacts, metadata)
        (output_dir / "report.html").write_text(html_output, encoding='utf-8')
        LOG.info("Saved HTML: report.html")
