"""Thin wrapper around an OpenAI-compatible chat + embeddings API.

Works against api.openai.com or a local Ollama server started with
`ollama serve` (point LLM_BASE_URL at http://localhost:11434/v1).
"""
from __future__ import annotations

import re

from openai import OpenAI

from app import config
from app.templates_loader import Template

SYSTEM_PROMPT = """You are drafting a contract from a template. Rules:
- Use only the clauses in the given template as the base for the draft. Do not add unrelated clauses.
- Fill in only the details that are actually given in the user's request.
- Never invent party names, dates, dollar amounts, or other specifics that were not provided.
- Any detail that is not given in the request must stay as a placeholder written in capital letters
  inside square brackets, for example [PARTY A NAME] or [EFFECTIVE DATE]. Keep the template's own
  placeholder wording where nothing was provided.
- Output clean HTML only, using h1 for the title, h2 for section headings, p for paragraphs, and
  ol/li for numbered clauses. Do not include a DOCTYPE, html, head, or body tag, just the content."""


def _client() -> OpenAI:
    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY or "unused")


def embed_text(text: str, kind: str = "document") -> list[float]:
    """Embeds a template ("document") or a user request ("query").

    nomic-embed-text is trained with task prefixes and ranks noticeably worse
    without them, so they are added for that model family only.
    """
    if "nomic" in config.EMBED_MODEL.lower():
        text = ("search_query: " if kind == "query" else "search_document: ") + text
    client = _client()
    response = client.embeddings.create(model=config.EMBED_MODEL, input=text)
    return response.data[0].embedding


def generate_draft(request_text: str, templates: list[Template]) -> str:
    """Calls the chat model to draft a contract from the given template(s)."""
    client = _client()
    template_block = "\n\n---\n\n".join(f"TEMPLATE: {t.title}\n{t.text}" for t in templates)
    user_prompt = (
        f"User's request:\n{request_text}\n\n"
        f"Template(s) to use as the base:\n{template_block}"
    )
    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


RERANK_PROMPT = """You pick contract templates. Given a request and a numbered list of template
titles, reply with the numbers ordered from best to worst fit, comma separated, nothing else.
Judge by the type of document the person is asking for (for example an NDA, a contractor
agreement, a services agreement), not by the subject the contract is about."""


def rerank(request_text: str, candidates: list[Template]) -> list[Template]:
    """Re-orders the search shortlist by document type using the chat model.

    Retrieval scores mix document type with topic words ("an NDA for a software
    pilot" looks close to the pilot template), so the model makes the final call
    on the shortlist. Falls back to the original order on any parse problem.
    """
    if len(candidates) < 2:
        return candidates
    listing = "\n".join(f"{i + 1}. {t.title}" for i, t in enumerate(candidates))
    try:
        response = _client().chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": RERANK_PROMPT},
                {"role": "user", "content": f"Request: {request_text}\n\nTemplates:\n{listing}"},
            ],
            temperature=0,
        )
        numbers = [int(n) for n in re.findall(r"\d+", response.choices[0].message.content or "")]
    except Exception:
        return candidates
    order = []
    for n in numbers:
        if 1 <= n <= len(candidates) and candidates[n - 1] not in order:
            order.append(candidates[n - 1])
    return order + [t for t in candidates if t not in order]


# --- demo mode fallback (no LLM_API_KEY configured) ------------------------

_PLACEHOLDER_RE = re.compile(r"\[([A-Z0-9 /\-]+)\]")


def demo_draft(request_text: str, template: Template) -> str:
    """Turns the raw template text into HTML with placeholders intact.

    No network call. Used when LLM_API_KEY is not set, so the app still
    runs end to end with zero configuration.
    """
    lines = [line.strip() for line in template.text.splitlines() if line.strip()]
    html_parts: list[str] = []
    if lines:
        html_parts.append(f"<h1>{lines[0].title()}</h1>")
        for line in lines[1:]:
            if re.match(r"^\d+\.\s+[A-Z]", line):
                html_parts.append(f"<h2>{line}</h2>")
            else:
                html_parts.append(f"<p>{line}</p>")
    return "\n".join(html_parts)


def find_placeholders(html_or_text: str) -> list[str]:
    return sorted(set(_PLACEHOLDER_RE.findall(html_or_text)))
