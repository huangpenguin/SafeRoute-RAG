"""Shared fixtures: load demo questions from manifest.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "sample_docs" / "manifest.yaml"


def load_demo_questions() -> dict[str, list[dict[str, Any]]]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    return manifest.get("demo_questions", {})


@pytest.fixture(scope="session")
def demo_questions() -> dict[str, list[dict[str, Any]]]:
    return load_demo_questions()


def all_routed_cases() -> list[dict[str, Any]]:
    """Flatten safe + unsafe cases that carry a deterministic expected_route."""
    dq = load_demo_questions()
    cases: list[dict[str, Any]] = []
    for bucket in ("safe", "unsafe"):
        for item in dq.get(bucket, []):
            if "expected_route" in item:
                cases.append(item)
    return cases
