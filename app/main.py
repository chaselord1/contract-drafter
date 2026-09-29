"""FastAPI app: template search, AI drafting, and PDF export."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import config, llm, pdf
from app.search import TemplateIndex
from app.templates_loader import load_templates

app = FastAPI(title="Contract Drafter")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATIC_DIR = os.path.join(_ROOT, "static")

templates = load_templates()
embed_fn = llm.embed_text if not config.DEMO_MODE else None
index = TemplateIndex(templates, embed_fn=embed_fn)


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


class SearchHit(BaseModel):
    id: str
    title: str
    score: float


class SearchResponse(BaseModel):
    demo_mode: bool
    results: list[SearchHit]


class DraftRequest(BaseModel):
    query: str
    template_ids: list[str] | None = None
    top_k: int = 3


class DraftResponse(BaseModel):
    demo_mode: bool
    html: str
    template_ids_used: list[str]
    placeholders: list[str]


class ExportRequest(BaseModel):
    html: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": config.DEMO_MODE, "templates_loaded": len(templates)}


def _ranked(query: str, top_k: int):
    """Hybrid search for a shortlist, then a model re-rank when one is configured."""
    results = index.search(query, top_k=top_k, embed_fn=embed_fn)
    if config.DEMO_MODE:
        return results
    by_id = {r.template.id: r for r in results}
    order = llm.rerank(query, [r.template for r in results])
    return [by_id[t.id] for t in order]


@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    results = _ranked(req.query, req.top_k)
    return SearchResponse(
        demo_mode=config.DEMO_MODE,
        results=[SearchHit(id=r.template.id, title=r.template.title, score=r.score) for r in results],
    )


@app.post("/api/draft", response_model=DraftResponse)
def draft(req: DraftRequest) -> DraftResponse:
    if req.template_ids:
        chosen = [t for t in templates if t.id in req.template_ids]
    else:
        chosen = [r.template for r in _ranked(req.query, req.top_k)]

    if not chosen:
        return DraftResponse(demo_mode=config.DEMO_MODE, html="<p>No matching template found.</p>",
                              template_ids_used=[], placeholders=[])

    if config.DEMO_MODE:
        html = llm.demo_draft(req.query, chosen[0])
        banner = (
            '<p class="demo-banner"><strong>Demo mode:</strong> set LLM_API_KEY to generate a real, '
            "request-aware draft. This is the raw template with its placeholders.</p>"
        )
        html = banner + html
    else:
        html = llm.generate_draft(req.query, chosen)

    return DraftResponse(
        demo_mode=config.DEMO_MODE,
        html=html,
        template_ids_used=[t.id for t in chosen],
        placeholders=llm.find_placeholders(html),
    )


@app.post("/api/export")
def export(req: ExportRequest) -> Response:
    pdf_bytes = pdf.html_to_pdf(req.html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="contract-draft.pdf"'},
    )


@app.get("/")
def index_page() -> FileResponse:
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
