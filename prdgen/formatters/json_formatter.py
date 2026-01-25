"""JSON output formatter for artifacts"""
import json
from typing import Dict, List, Optional
from datetime import datetime

class JSONFormatter:
    """Converts markdown artifacts to structured JSON"""

    def format_all(self, artifacts: Dict[str, str], metadata: Optional[Dict] = None) -> str:
        """
        Convert all artifacts to structured JSON.

        Args:
            artifacts: Dict of artifact_name -> markdown content
            metadata: Optional generation metadata

        Returns:
            JSON string with structured output

        Output structure:
        {
          "generated_at": "2026-01-24T...",
          "format_version": "1.0",
          "metadata": {...},
          "artifacts": {
            "prd": {
              "type": "prd",
              "content_markdown": "...",
              "content_structured": {
                "sections": [...]
              },
              "char_count": 1234
            },
            ...
          }
        }
        """
        output = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "format_version": "1.0",
            "metadata": metadata or {},
            "artifacts": {}
        }

        for name, markdown_content in artifacts.items():
            # Remove .md extension if present for consistency
            artifact_name = name.replace('.md', '')

            output["artifacts"][artifact_name] = {
                "type": artifact_name,
                "content_markdown": markdown_content,
                "content_structured": self._parse_markdown(artifact_name, markdown_content),
                "char_count": len(markdown_content),
                "line_count": len(markdown_content.split('\n'))
            }

        return json.dumps(output, indent=2, ensure_ascii=False)

    def _parse_markdown(self, artifact_type: str, markdown: str) -> dict:
        """
        Parse markdown into structured data.
        Extracts sections, headers, lists, etc.

        Args:
            artifact_type: Type of artifact (for context)
            markdown: Markdown content

        Returns:
            Structured representation of the markdown
        """
        lines = markdown.split('\n')
        sections = []
        current_section = None
        current_subsection = None

        for line in lines:
            line_stripped = line.strip()

            if line_stripped.startswith('## '):
                # H2 - Main section
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "level": 2,
                    "title": line_stripped[3:].strip(),
                    "content": [],
                    "subsections": []
                }
                current_subsection = None

            elif line_stripped.startswith('### '):
                # H3 - Subsection
                if current_section:
                    if current_subsection:
                        current_section["subsections"].append(current_subsection)
                    current_subsection = {
                        "level": 3,
                        "title": line_stripped[4:].strip(),
                        "content": []
                    }

            elif line_stripped.startswith('#### '):
                # H4 - Sub-subsection
                if current_subsection:
                    current_subsection["content"].append({
                        "type": "heading",
                        "level": 4,
                        "text": line_stripped[5:].strip()
                    })
                elif current_section:
                    current_section["content"].append({
                        "type": "heading",
                        "level": 4,
                        "text": line_stripped[5:].strip()
                    })

            elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
                # List item
                item = line_stripped[2:].strip()
                target = current_subsection if current_subsection else current_section
                if target:
                    target["content"].append({
                        "type": "list_item",
                        "text": item
                    })

            elif line_stripped.startswith('1. ') or line_stripped.startswith('2. '):
                # Numbered list
                # Extract the number and item
                parts = line_stripped.split('. ', 1)
                if len(parts) == 2:
                    item = parts[1].strip()
                    target = current_subsection if current_subsection else current_section
                    if target:
                        target["content"].append({
                            "type": "numbered_item",
                            "text": item
                        })

            elif line_stripped.startswith('**') and line_stripped.endswith('**'):
                # Bold text (potential label)
                text = line_stripped.strip('*').strip()
                target = current_subsection if current_subsection else current_section
                if target:
                    target["content"].append({
                        "type": "bold",
                        "text": text
                    })

            elif line_stripped:
                # Regular paragraph text
                target = current_subsection if current_subsection else current_section
                if target:
                    target["content"].append({
                        "type": "paragraph",
                        "text": line_stripped
                    })

        # Add last subsection and section
        if current_subsection and current_section:
            current_section["subsections"].append(current_subsection)
        if current_section:
            sections.append(current_section)

        return {
            "sections": sections,
            "section_count": len(sections),
            "has_subsections": any(s.get("subsections") for s in sections)
        }
