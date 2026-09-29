"""Ranks templates against a plain-language request.

Two modes:
- With an LLM_API_KEY configured: embeddings are computed once at startup
  for every template, and a query is ranked by cosine similarity in numpy.
- Without a key (demo mode): a small pure-Python BM25 implementation ranks
  templates by term overlap. No network call, no numpy needed for scoring.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from app import config
from app.templates_loader import Template

_TOKEN_RE = re.compile(r"[a-z0-9]+")
EMBED_WEIGHT = 0.5

# Common abbreviations people type in requests, expanded to the words the
# templates actually use.
_SYNONYMS = {
    "nda": ["non", "disclosure", "confidentiality"],
    "sow": ["statement", "work"],
    "saas": ["software", "service"],
    "poc": ["pilot", "evaluation"],
    "freelance": ["independent", "contractor"],
    "freelancer": ["independent", "contractor"],
    "trial": ["pilot", "evaluation"],
}

# How much a hit on the template title counts next to a hit in the body.
# The title names the document type, which matters more than topic words.
TITLE_WEIGHT = 3.0


def tokenize(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        expanded.extend(_SYNONYMS.get(token, []))
    return expanded


@dataclass
class SearchResult:
    template: Template
    score: float


class BM25:
    """Minimal BM25 over a fixed set of documents, no external deps."""

    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.doc_lengths = [len(doc) for doc in documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(documents) if documents else 0.0
        self.doc_freqs: list[dict[str, int]] = []
        df: dict[str, int] = {}
        for doc in documents:
            freqs: dict[str, int] = {}
            for term in doc:
                freqs[term] = freqs.get(term, 0) + 1
            self.doc_freqs.append(freqs)
            for term in freqs:
                df[term] = df.get(term, 0) + 1
        self.idf: dict[str, float] = {}
        n = len(documents)
        for term, freq in df.items():
            self.idf[term] = math.log(1 + (n - freq + 0.5) / (freq + 0.5))

    def score(self, query_terms: list[str], doc_index: int) -> float:
        score = 0.0
        freqs = self.doc_freqs[doc_index]
        doc_len = self.doc_lengths[doc_index]
        for term in query_terms:
            if term not in freqs:
                continue
            idf = self.idf.get(term, 0.0)
            f = freqs[term]
            denom = f + self.k1 * (1 - self.b + self.b * doc_len / (self.avg_doc_length or 1))
            score += idf * (f * (self.k1 + 1)) / denom
        return score

    def rank(self, query: str) -> list[float]:
        query_terms = tokenize(query)
        return [self.score(query_terms, i) for i in range(len(self.documents))]


class TemplateIndex:
    """Holds the loaded templates plus whatever search backend is active."""

    def __init__(self, templates: list[Template], embed_fn=None):
        self.templates = templates
        self._bm25 = BM25([tokenize(t.text) for t in templates])
        self._title_bm25 = BM25([tokenize(t.title) for t in templates])
        self._embeddings: np.ndarray | None = None
        if embed_fn is not None and not config.DEMO_MODE:
            vectors = [embed_fn(t.text) for t in templates]
            self._embeddings = np.array(vectors, dtype=np.float32)

    @property
    def using_embeddings(self) -> bool:
        return self._embeddings is not None

    def search(self, query: str, top_k: int = 3, embed_fn=None) -> list[SearchResult]:
        if self._embeddings is not None and embed_fn is not None:
            return self._search_embeddings(query, top_k, embed_fn)
        return self._search_bm25(query, top_k)

    def _keyword_scores(self, query: str) -> list[float]:
        body = self._bm25.rank(query)
        title = self._title_bm25.rank(query)
        return [b + TITLE_WEIGHT * t for b, t in zip(body, title)]

    def _search_bm25(self, query: str, top_k: int) -> list[SearchResult]:
        scores = self._keyword_scores(query)
        ranked = sorted(zip(self.templates, scores), key=lambda pair: pair[1], reverse=True)
        return [SearchResult(template=t, score=s) for t, s in ranked[:top_k]]

    def _search_embeddings(self, query: str, top_k: int, embed_fn) -> list[SearchResult]:
        # Hybrid ranking: small embedding models tend to latch onto topic words
        # ("software pilot") and miss the document type ("NDA"), so the cosine
        # score is blended with BM25 keyword overlap. Both are scaled to 0..1
        # across the template pool before mixing.
        try:
            query_vec = np.array(embed_fn(query, kind="query"), dtype=np.float32)
        except TypeError:  # plain embed functions (e.g. test stubs) take one argument
            query_vec = np.array(embed_fn(query), dtype=np.float32)
        query_norm = query_vec / (np.linalg.norm(query_vec) or 1.0)
        doc_norms = self._embeddings / (
            np.linalg.norm(self._embeddings, axis=1, keepdims=True) + 1e-10
        )
        sims = doc_norms @ query_norm
        keyword = np.array(self._keyword_scores(query), dtype=np.float32)

        def scale(values: np.ndarray) -> np.ndarray:
            span = float(values.max() - values.min())
            return (values - values.min()) / span if span > 0 else np.zeros_like(values)

        hybrid = EMBED_WEIGHT * scale(sims) + (1 - EMBED_WEIGHT) * scale(keyword)
        order = np.argsort(-hybrid)[:top_k]
        return [SearchResult(template=self.templates[i], score=float(hybrid[i])) for i in order]
