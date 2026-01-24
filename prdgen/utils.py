import re
from typing import List

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
