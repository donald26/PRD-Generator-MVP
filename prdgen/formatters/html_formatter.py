"""HTML report generator for artifacts"""
from typing import Dict, Optional
from datetime import datetime
import re

class HTMLFormatter:
    """Generates professional HTML reports from artifacts"""

    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PRD Artifacts Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        .container {{
            display: flex;
            min-height: 100vh;
        }}
        .sidebar {{
            width: 280px;
            background: #2c3e50;
            color: white;
            padding: 2rem 1rem;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }}
        .sidebar h1 {{
            font-size: 1.5rem;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #34495e;
        }}
        .sidebar nav a {{
            display: block;
            color: #ecf0f1;
            text-decoration: none;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
            transition: all 0.2s;
            font-size: 0.95rem;
        }}
        .sidebar nav a:hover {{
            background: #34495e;
            transform: translateX(4px);
        }}
        .sidebar nav a.active {{
            background: #3498db;
            font-weight: 500;
        }}
        .content {{
            flex: 1;
            padding: 3rem;
            max-width: 1200px;
        }}
        .header {{
            margin-bottom: 3rem;
        }}
        .header h1 {{
            font-size: 2.5rem;
            color: #2c3e50;
            margin-bottom: 0.5rem;
        }}
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 1.1rem;
        }}
        .artifact {{
            background: white;
            padding: 2.5rem;
            margin-bottom: 3rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .artifact h2 {{
            color: #2c3e50;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 3px solid #3498db;
            font-size: 1.8rem;
        }}
        .artifact h3 {{
            color: #34495e;
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-size: 1.4rem;
        }}
        .artifact h4 {{
            color: #555;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            font-size: 1.1rem;
        }}
        .artifact ul, .artifact ol {{
            margin-left: 2rem;
            margin-bottom: 1rem;
        }}
        .artifact li {{
            margin-bottom: 0.5rem;
        }}
        .artifact p {{
            margin-bottom: 1rem;
            line-height: 1.7;
        }}
        .artifact code {{
            background: #f8f9fa;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #e74c3c;
        }}
        .artifact pre {{
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            margin-bottom: 1rem;
            border-left: 3px solid #3498db;
        }}
        .artifact pre code {{
            background: none;
            padding: 0;
            color: #333;
        }}
        .artifact blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 1rem;
            margin: 1rem 0;
            color: #555;
            font-style: italic;
        }}
        .artifact strong {{
            color: #2c3e50;
            font-weight: 600;
        }}
        .artifact em {{
            color: #555;
        }}
        .artifact table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        .artifact table th, .artifact table td {{
            border: 1px solid #ddd;
            padding: 0.75rem;
            text-align: left;
        }}
        .artifact table th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        .metadata {{
            background: #e8f4f8;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }}
        .metadata strong {{
            color: #2c3e50;
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-right: 0.5rem;
        }}
        .badge-primary {{
            background: #3498db;
            color: white;
        }}
        .badge-success {{
            background: #2ecc71;
            color: white;
        }}
        .badge-info {{
            background: #16a085;
            color: white;
        }}
        @media print {{
            .sidebar {{ display: none; }}
            .content {{ padding: 1rem; max-width: 100%; }}
            .artifact {{ box-shadow: none; page-break-inside: avoid; }}
        }}
        @media (max-width: 768px) {{
            .container {{ flex-direction: column; }}
            .sidebar {{ width: 100%; height: auto; position: relative; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <h1>📄 PRD Report</h1>
            <nav>
                {navigation}
            </nav>
            <div class="metadata">
                <strong>Generated:</strong><br>
                {generated_at}<br><br>
                {metadata_info}
            </div>
        </aside>
        <main class="content">
            <div class="header">
                <h1>Product Requirements Documentation</h1>
                <p class="subtitle">Generated Artifacts and Analysis</p>
            </div>
            {artifacts_html}
        </main>
    </div>
    <script>
        // Smooth scrolling for navigation
        document.querySelectorAll('.sidebar nav a').forEach(link => {{
            link.addEventListener('click', function(e) {{
                e.preventDefault();
                const targetId = this.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    // Update active state
                    document.querySelectorAll('.sidebar nav a').forEach(a => a.classList.remove('active'));
                    this.classList.add('active');
                }}
            }});
        }});

        // Highlight current section on scroll
        const observerOptions = {{
            root: null,
            rootMargin: '-20% 0px -70% 0px',
            threshold: 0
        }};

        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const id = entry.target.id;
                    document.querySelectorAll('.sidebar nav a').forEach(a => {{
                        a.classList.remove('active');
                        if (a.getAttribute('href') === '#' + id) {{
                            a.classList.add('active');
                        }}
                    }});
                }}
            }});
        }}, observerOptions);

        document.querySelectorAll('.artifact').forEach(section => {{
            observer.observe(section);
        }});
    </script>
</body>
</html>
    """

    ARTIFACT_ICONS = {
        "corpus_summary": "📋",
        "prd": "📝",
        "capabilities": "🗺️",
        "capability_cards": "🎴",
        "epics": "🎯",
        "features": "✨",
        "user_stories": "👤",
        "lean_canvas": "📊"
    }

    ARTIFACT_TITLES = {
        "corpus_summary": "Corpus Summary",
        "prd": "Product Requirements Document",
        "capabilities": "Capability Map",
        "capability_cards": "Capability Cards",
        "epics": "Epics",
        "features": "Features",
        "user_stories": "User Stories",
        "lean_canvas": "Lean Canvas"
    }

    def generate_report(self, artifacts: Dict[str, str], metadata: Optional[Dict] = None) -> str:
        """
        Generate a complete HTML report.

        Args:
            artifacts: Dict of artifact_name -> markdown content
            metadata: Optional generation metadata

        Returns:
            Complete HTML document as string
        """
        # Convert markdown to HTML for each artifact
        artifacts_html = ""
        navigation = ""

        for name, markdown_content in artifacts.items():
            # Remove .md extension if present
            artifact_key = name.replace('.md', '')

            icon = self.ARTIFACT_ICONS.get(artifact_key, "📄")
            title = self.ARTIFACT_TITLES.get(artifact_key, artifact_key.replace('_', ' ').title())

            html_content = self._markdown_to_html(markdown_content)

            artifacts_html += f"""
            <section class="artifact" id="{artifact_key}">
                <h2>{icon} {title}</h2>
                {html_content}
            </section>
            """

            navigation += f'<a href="#{artifact_key}">{icon} {title}</a>\n'

        # Build metadata info
        metadata_info = ""
        if metadata:
            if "model_id" in metadata:
                metadata_info += f"<strong>Model:</strong> {metadata['model_id']}<br>"
            if "timings" in metadata and metadata["timings"]:
                total_time = sum(metadata["timings"].values())
                metadata_info += f"<strong>Total Time:</strong> {total_time:.1f}s<br>"
            if "cache_hits" in metadata:
                metadata_info += f"<strong>Cache Hits:</strong> {metadata['cache_hits']}<br>"

        # Fill template
        return self.HTML_TEMPLATE.format(
            navigation=navigation,
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            metadata_info=metadata_info or "No metadata available",
            artifacts_html=artifacts_html
        )

    def _markdown_to_html(self, markdown: str) -> str:
        """
        Convert markdown to HTML (simplified implementation).

        Note: This is a basic converter. For production, consider using
        a library like python-markdown, but this avoids dependencies.
        """
        html = markdown

        # Code blocks (```)
        html = re.sub(
            r'```(\w*)\n(.*?)\n```',
            r'<pre><code class="language-\1">\2</code></pre>',
            html,
            flags=re.DOTALL
        )

        # Inline code (`)
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # Bold (**text**)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

        # Italic (*text*)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Headers
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Blockquotes (>)
        html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

        # Links [text](url)
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        # Unordered lists
        lines = html.split('\n')
        processed_lines = []
        in_list = False

        for line in lines:
            if re.match(r'^[-*] ', line):
                if not in_list:
                    processed_lines.append('<ul>')
                    in_list = True
                item = re.sub(r'^[-*] ', '', line)
                processed_lines.append(f'<li>{item}</li>')
            else:
                if in_list:
                    processed_lines.append('</ul>')
                    in_list = False
                if line.strip() and not line.strip().startswith('<'):
                    # Regular paragraph
                    processed_lines.append(f'<p>{line}</p>')
                else:
                    processed_lines.append(line)

        if in_list:
            processed_lines.append('</ul>')

        html = '\n'.join(processed_lines)

        # Clean up empty paragraphs
        html = re.sub(r'<p></p>', '', html)
        html = re.sub(r'<p>\s*</p>', '', html)

        return html
