from app.llm import demo_draft, find_placeholders
from app.templates_loader import load_templates


def test_demo_draft_preserves_placeholders():
    templates = load_templates()
    nda = next(t for t in templates if t.id == "mutual-nda")
    html = demo_draft("mutual NDA for two companies", nda)
    assert "[PARTY A NAME]" in html
    assert "[EFFECTIVE DATE]" in html


def test_demo_draft_returns_html_tags():
    templates = load_templates()
    nda = next(t for t in templates if t.id == "mutual-nda")
    html = demo_draft("mutual NDA", nda)
    assert "<h1>" in html
    assert "<h2>" in html or "<p>" in html


def test_find_placeholders():
    placeholders = find_placeholders("Between [PARTY A NAME] and [PARTY B NAME] as of [EFFECTIVE DATE].")
    assert placeholders == ["EFFECTIVE DATE", "PARTY A NAME", "PARTY B NAME"]
