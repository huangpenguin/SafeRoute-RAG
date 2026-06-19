#!/usr/bin/env python3
"""Run the route regression over manifest demo_questions and emit a result table.

Usage:
    uv run python scripts/run_route_eval.py            # routing only
    uv run python scripts/run_route_eval.py --retrieval # also check Top-K expected_docs

Hard-rule cases run fully offline. Semantic-audit cases require AIAND_API_KEY;
without it they are reported as SKIPPED rather than failing.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config_loader import ConfigLoader  # noqa: E402
from src.llm_client import LLMClient  # noqa: E402
from src.router import HybridRouter  # noqa: E402

MANIFEST_PATH: Path = ROOT / "sample_docs" / "manifest.yaml"
OUTPUT_PATH: Path = ROOT / "eval_results.md"


@dataclass
class RowResult:
    case_id: str
    bucket: str
    expected: str
    actual: str
    layer: str
    detail: str
    status: str
    retrieval: str = "-"


def _load_cases() -> list[dict[str, Any]]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)
    dq = manifest.get("demo_questions", {})
    cases: list[dict[str, Any]] = []
    for bucket in ("safe", "unsafe"):
        for item in dq.get(bucket, []):
            if "expected_route" in item:
                item = {**item, "_bucket": bucket}
                cases.append(item)
    return cases


def _evaluate(retrieval: bool) -> list[RowResult]:
    config = ConfigLoader().get()
    router = HybridRouter(config, LLMClient(config))
    has_key = bool(os.environ.get("AIAND_API_KEY"))

    kb = None
    if retrieval:
        from src.database import LocalKnowledgeBase

        kb = LocalKnowledgeBase(config.rag)
        if kb.count() == 0:
            kb.ingest_manifest(reset=True)

    rows: list[RowResult] = []
    for case in _load_cases():
        cid = case["id"]
        bucket = case["_bucket"]
        expected = case["expected_route"]

        if not has_key:
            rows.append(RowResult(cid, bucket, expected, "-", "semantic_audit", "no API key", "SKIPPED"))
            continue

        try:
            decision = router.route(case["question"])
        except Exception as exc:  # noqa: BLE001 - surface as table cell, not crash
            rows.append(RowResult(cid, bucket, expected, "ERROR", "-", str(exc)[:60], "ERROR"))
            continue

        status = "PASS" if decision.label == expected else "FAIL"
        detail = decision.reason or (", ".join(decision.matched_keywords) or "-")

        retrieval_cell = "-"
        if kb is not None:
            expected_docs = set(case.get("expected_docs", []))
            allowed = None if decision.label == "UNSAFE" else {"public", "uploaded"}
            hit_docs = [c.doc_id for c in kb.retrieve(case["question"], allowed_tiers=allowed)]
            ok = bool(expected_docs & set(hit_docs))
            retrieval_cell = ("OK " if ok else "MISS ") + "/".join(hit_docs[:3])

        rows.append(RowResult(cid, bucket, expected, decision.label, decision.layer, detail, status, retrieval_cell))
    return rows


def _render_table(rows: list[RowResult], retrieval: bool) -> str:
    header = "| ID | Bucket | Expected | Actual | Layer | Detail | Status |"
    sep = "| --- | --- | --- | --- | --- | --- | --- |"
    if retrieval:
        header = header[:-1] + " Retrieval (expected_docs hit) |"
        sep = sep[:-1] + " --- |"
    lines = [header, sep]
    for r in rows:
        cells = [r.case_id, r.bucket, r.expected, r.actual, r.layer, r.detail.replace("|", "/"), r.status]
        if retrieval:
            cells.append(r.retrieval)
        lines.append("| " + " | ".join(cells) + " |")

    graded = [r for r in rows if r.status in {"PASS", "FAIL"}]
    passed = sum(1 for r in graded if r.status == "PASS")
    skipped = sum(1 for r in rows if r.status == "SKIPPED")
    summary = (
        f"\n**Summary:** {passed}/{len(graded)} routed cases passed"
        f"  |  {skipped} skipped (no API key)"
        f"  |  {len(rows)} total\n"
    )
    return "# SafeRoute-RAG Route Evaluation\n\n" + "\n".join(lines) + "\n" + summary


def main() -> None:
    parser = argparse.ArgumentParser(description="SafeRoute-RAG route regression runner")
    parser.add_argument("--retrieval", action="store_true", help="also check Top-K expected_docs")
    args = parser.parse_args()

    rows = _evaluate(retrieval=args.retrieval)
    table = _render_table(rows, retrieval=args.retrieval)
    OUTPUT_PATH.write_text(table, encoding="utf-8")
    print(table)
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
