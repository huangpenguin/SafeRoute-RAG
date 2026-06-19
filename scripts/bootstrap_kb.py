#!/usr/bin/env python3
"""Warm up the embedding model and ingest manifest into ChromaDB.

Used at Docker build time (HF Spaces) and safe to run manually:
    uv run python scripts/bootstrap_kb.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config_loader import ConfigLoader  # noqa: E402
from src.database import LocalKnowledgeBase  # noqa: E402


def main() -> None:
    cfg = ConfigLoader().get()
    kb = LocalKnowledgeBase(cfg.rag)
    chunk_count = kb.ingest_manifest(reset=True)
    print(f"bootstrap_kb: ingested {chunk_count} chunks into {cfg.rag.persist_dir}")
    if chunk_count == 0:
        raise SystemExit("bootstrap_kb failed: no chunks ingested (check sample_docs/)")


if __name__ == "__main__":
    main()
