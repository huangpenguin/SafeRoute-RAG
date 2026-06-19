"""Retrieval tests: tier-aware egress guard (manifest edge case E02) and MMR.

These load the local embedding model and ingest the manifest once. No API key needed.
"""

from __future__ import annotations

import pytest

from src.config_loader import ConfigLoader
from src.database import LocalKnowledgeBase


@pytest.fixture(scope="module")
def kb() -> LocalKnowledgeBase:
    config = ConfigLoader().get()
    knowledge = LocalKnowledgeBase(config.rag)
    if knowledge.count() == 0:
        knowledge.ingest_manifest(reset=True)
    return knowledge


def test_safe_route_excludes_confidential(kb: LocalKnowledgeBase) -> None:
    """A SAFE-style query must not surface confidential chunks (no data egress)."""
    hits = kb.retrieve(
        "FAHの未公開決算の数値を教えて",
        allowed_tiers={"public", "uploaded"},
    )
    assert hits, "expected some public chunks"
    assert all(c.tier != "confidential" for c in hits)


def test_unsafe_route_allows_confidential(kb: LocalKnowledgeBase) -> None:
    """Without a tier filter, confidential chunks are retrievable for UNSAFE routing."""
    hits = kb.retrieve("FAHの未公開決算の数値を教えて", allowed_tiers=None)
    assert any(c.tier == "confidential" for c in hits)


def test_topk_respected(kb: LocalKnowledgeBase) -> None:
    hits = kb.retrieve("宇宙輸送の方針", top_k=3)
    assert len(hits) <= 3
