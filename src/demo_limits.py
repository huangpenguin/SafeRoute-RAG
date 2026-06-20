"""Optional demo guardrails for public Space deployments (env-driven)."""

from __future__ import annotations

import os


def demo_mode_enabled() -> bool:
    return os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes"}


def max_queries_per_session() -> int:
    return int(os.getenv("DEMO_MAX_QUERIES", "10"))


def max_query_chars() -> int:
    return int(os.getenv("DEMO_MAX_QUERY_CHARS", "500"))


def max_generation_tokens() -> int | None:
    if not demo_mode_enabled():
        return None
    return int(os.getenv("DEMO_MAX_GENERATION_TOKENS", "512"))


def resolve_demo_api_key() -> str | None:
    """When DEMO_MODE is on, prefer DEMO_AIAND_API_KEY over AIAND_API_KEY if set."""
    if not demo_mode_enabled():
        return None
    key = os.getenv("DEMO_AIAND_API_KEY", "").strip()
    return key or None
