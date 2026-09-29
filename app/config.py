"""Tiny .env loader plus config values, no python-dotenv dependency."""
from __future__ import annotations

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_ROOT, ".env")


def _load_dotenv(path: str) -> None:
    """Reads KEY=VALUE lines from a .env file into os.environ, if present.

    Does not override variables already set in the real environment.
    """
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(_ENV_PATH)

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")

# Demo mode kicks in whenever no API key is configured: search falls back to
# BM25 and drafting falls back to a placeholder-filled template instead of
# a real LLM call.
DEMO_MODE = not bool(LLM_API_KEY)
