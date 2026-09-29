from app.search import TemplateIndex
from app.templates_loader import load_templates


def test_bm25_ranks_nda_first_for_nda_query():
    templates = load_templates()
    index = TemplateIndex(templates)
    results = index.search("mutual non-disclosure agreement between two companies", top_k=3)
    assert results[0].template.id == "mutual-nda"


def test_bm25_ranks_contractor_agreement_for_contractor_query():
    templates = load_templates()
    index = TemplateIndex(templates)
    results = index.search("independent contractor agreement for freelance work", top_k=3)
    assert results[0].template.id == "independent-contractor-agreement"
