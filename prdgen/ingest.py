import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from .utils import read_text

LOG = logging.getLogger("prdgen.ingest")

TEXT_EXTS = {".txt", ".md", ".markdown", ".rst", ".log"}
DOCX_EXTS = {".docx"}

@dataclass
class IngestedDoc:
    path: str
    kind: str  # "text" | "docx" | "unknown"
    content: str

def _read_docx(path: Path) -> str:
    try:
        from docx import Document  # python-docx
    except Exception as e:
        raise RuntimeError("python-docx is required to read .docx files. Install: pip install python-docx") from e

    doc = Document(str(path))
    parts = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts).strip()

def ingest_folder(
    input_dir: str,
    include_exts: Optional[List[str]] = None,
    max_files: int = 25,
    max_chars_per_file: int = 12000,
) -> List[IngestedDoc]:
    """Read multiple documents from a folder and return normalized text.
    Supports: .txt/.md/... and .docx (via python-docx).
    """
    root = Path(input_dir)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"input_dir is not a directory: {input_dir}")

    exts = None
    if include_exts:
        exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in include_exts}

    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if exts is not None and ext not in exts:
            continue
        if exts is None and ext not in (TEXT_EXTS | DOCX_EXTS):
            continue
        files.append(p)

    files = sorted(files)[:max_files]
    if not files:
        raise RuntimeError("No supported files found in input folder. Supported: txt/md/log/docx (or pass --include-exts).")

    docs: List[IngestedDoc] = []
    for p in files:
        ext = p.suffix.lower()
        try:
            if ext in TEXT_EXTS:
                content = read_text(str(p))
                kind = "text"
            elif ext in DOCX_EXTS:
                content = _read_docx(p)
                kind = "docx"
            else:
                content = read_text(str(p))
                kind = "unknown"
        except Exception as e:
            LOG.warning("Skipping unreadable file: %s (%s)", p, e)
            continue

        content = (content or "").strip()
        if not content:
            continue
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n\n[TRUNCATED]\n"

        docs.append(IngestedDoc(path=str(p), kind=kind, content=content))

    if not docs:
        raise RuntimeError("No readable non-empty files found after filtering.")
    return docs

def format_corpus(docs: List[IngestedDoc]) -> str:
    """Create a single multi-doc corpus string with clear boundaries."""
    parts = []
    for d in docs:
        parts.append(f"=== FILE: {d.path} (type={d.kind}) ===\n{d.content}\n")
    return "\n".join(parts).strip() + "\n"
