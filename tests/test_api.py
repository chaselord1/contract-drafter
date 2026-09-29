from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["templates_loaded"] == 6


def test_search_endpoint_ranks_nda_first():
    res = client.post("/api/search", json={"query": "mutual NDA between two companies", "top_k": 3})
    assert res.status_code == 200
    body = res.json()
    assert body["results"][0]["id"] == "mutual-nda"


def test_draft_endpoint_returns_html_with_placeholder():
    res = client.post("/api/draft", json={"query": "mutual NDA between two companies, California law"})
    assert res.status_code == 200
    body = res.json()
    assert body["demo_mode"] is True
    assert "<h1>" in body["html"] or "<p>" in body["html"]
    assert len(body["placeholders"]) > 0


def test_export_endpoint_returns_pdf_bytes():
    res = client.post("/api/export", json={"html": "<h1>Test</h1><p>[PLACEHOLDER]</p>"})
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
