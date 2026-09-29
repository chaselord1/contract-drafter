"""Loads contract templates from the templates/ folder.

Supports plain .txt files and .docx files (via python-docx). Each template
is exposed as a dict with an id, a display title, and its full text body.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from docx import Document
except ImportError:  # pragma: no cover - python-docx is a required dep
    Document = None

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")


@dataclass
class Template:
    id: str
    title: str
    text: str


_SMALL_WORDS = {"and", "or", "of", "for", "the", "a", "an", "to"}
_SPECIAL_CASE = {"saas": "SaaS", "nda": "NDA", "sow": "SOW"}


def _nice_title(raw: str) -> str:
    """Title case that keeps SaaS/NDA readable and small joining words lowercase."""
    words = raw.replace("_", " ").split()
    titled = []
    for i, word in enumerate(words):
        parts = word.split("-")
        fixed = []
        for part in parts:
            low = part.lower()
            if low in _SPECIAL_CASE:
                fixed.append(_SPECIAL_CASE[low])
            elif i > 0 and low in _SMALL_WORDS and len(parts) == 1:
                fixed.append(low)
            else:
                fixed.append(part.capitalize())
        titled.append("-".join(fixed))
    return " ".join(titled)


def _title_from_filename(filename: str) -> str:
    return _nice_title(os.path.splitext(filename)[0].replace("-", " "))


def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_docx(path: str) -> str:
    if Document is None:
        raise RuntimeError("python-docx is required to load .docx templates")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def load_templates(templates_dir: str = TEMPLATES_DIR) -> list[Template]:
    """Reads every .txt and .docx file in templates_dir into Template objects."""
    templates: list[Template] = []
    if not os.path.isdir(templates_dir):
        return templates

    for filename in sorted(os.listdir(templates_dir)):
        path = os.path.join(templates_dir, filename)
        if not os.path.isfile(path):
            continue

        lower = filename.lower()
        if lower.endswith(".txt"):
            text = _read_txt(path)
        elif lower.endswith(".docx"):
            text = _read_docx(path)
        else:
            continue

        template_id = os.path.splitext(filename)[0]
        title = _nice_title(text.splitlines()[0].strip()) if text.strip() else _title_from_filename(filename)
        templates.append(Template(id=template_id, title=title, text=text))

    return templates
