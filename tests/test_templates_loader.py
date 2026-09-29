from app.templates_loader import load_templates


def test_loads_all_six_templates():
    templates = load_templates()
    assert len(templates) == 6


def test_templates_have_text_and_placeholders():
    templates = load_templates()
    for t in templates:
        assert t.text.strip()
        assert "[" in t.text and "]" in t.text
