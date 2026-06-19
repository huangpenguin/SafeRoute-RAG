#!/usr/bin/env python3
"""Extract and clean public corpus from legacy PDFs into RAG-ready Markdown."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[1]
LEGACY_DIR = ROOT / "sample_docs" / "public" / "legacy"
OUTPUT_DIR = ROOT / "sample_docs" / "public"

# Single-char lines from vertical PDF section headers (JSAT IR reports).
_VERTICAL_SECTION_CHARS = frozenset("価値創造を支えるガバナンス資料データセクションストーリー実践")


@dataclass(frozen=True)
class ExtractSpec:
    doc_id: str
    legacy_filename: str
    output_filename: str
    title: str
    source_url: str
    pages: list[int]  # 1-based inclusive page numbers
    page_postprocessors: dict[int, Callable[[str], str]] | None = None


def _slim_smu_only(text: str) -> str:
    """Page 11: keep SMU block, drop STRX and vendor footer."""
    marker = "統合化計算機（SMU）"
    if marker not in text:
        return text
    start = text.find(marker)
    for end_marker in ("Sバンドトランスポンダ", "STRX", "三菱電機"):
        end = text.find(end_marker, start + len(marker))
        if end != -1:
            return text[start:end].strip()
    return text[start:].strip()


SPECS: list[ExtractSpec] = [
    ExtractSpec(
        doc_id="JAXA_H3",
        legacy_filename="JAXA_H3_PressKit.pdf.pdf",
        output_filename="jaxa_h3_overview.md",
        title="JAXA H3ロケット 開発目的・概要（Press Kit 抜粋）",
        source_url="https://www.jaxa.jp/projects/rockets/h3/",
        pages=[5, 12, 13, 14, 18],
    ),
    ExtractSpec(
        doc_id="JAXA_SLIM",
        legacy_filename="JAXA_SLIM_Report.pdf",
        output_filename="jaxa_slim_overview.md",
        title="SLIM ミッション概要・統合化計算機(SMU)（抜粋）",
        source_url="https://www.jaxa.jp/projects/slim/",
        pages=[5, 6, 7, 8, 11],
        page_postprocessors={11: _slim_smu_only},
    ),
    ExtractSpec(
        doc_id="MHI_Report",
        legacy_filename="MHI_Report_2024.pdf",
        output_filename="mhi_integrated_report.md",
        title="三菱重工 統合レポート2024 宇宙・防衛分野（抜粋）",
        source_url="https://www.mhi.com/finance/library/integrated_report.html",
        pages=[3, 59],  # drop p58 chart debris
    ),
    ExtractSpec(
        doc_id="IHI_Integrated",
        legacy_filename="IHI_Integrated_2023.pdf",
        output_filename="ihi_aerospace_defense.md",
        title="IHI 統合報告書2023 航空・宇宙・防衛（抜粋）",
        source_url="https://www.ihi.co.jp/company/ir/",
        pages=[39, 42, 43],
    ),
    ExtractSpec(
        doc_id="JSAT_Integrated",
        legacy_filename="JSAT_Integrated_2023.pdf",
        output_filename="jsat_space_vision.md",
        title="スカパーJSAT 統合報告書2023 宇宙事業（抜粋）",
        source_url="https://www.skyperfectjsat.space/jsat/corporate/ir/",
        pages=[3, 38, 42],  # p3 事業ビジョン; drop p41 chart/vertical noise
    ),
    ExtractSpec(
        doc_id="CAO_Plan",
        legacy_filename="CAO_SpaceBasicPlan.pdf",
        output_filename="cao_space_basic_plan.md",
        title="令和6年度 宇宙基本計画工程表 宇宙輸送（抜粋）",
        source_url="https://www8.cao.go.jp/space/",
        pages=[49, 50, 51, 52],
    ),
]

NOISE_LINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^H3 & ALOS-3 PRESSKIT(?: JAXA \d+)?$"),
    re.compile(r"^JAXA$"),
    re.compile(r"^SKY Perfect JSAT Integrated Report 2023$"),
    re.compile(r"^IHI 統合報告書 2023 \d+$"),
    re.compile(r"^MITSUBISHI HEAVY INDUSTRIES GROUP(?: \d+)?$"),
    re.compile(r"^MHI REPORT 2024$"),
    re.compile(r"^Business Strategies$"),
    re.compile(r"^Overview$"),
    re.compile(r"^Messages from Management$"),
    re.compile(r"^Special Feature$"),
    re.compile(r"^Governance & Sustainability$"),
    re.compile(r"^Performance Data$"),
    re.compile(r"^FOCUS$"),
    re.compile(r"^事業概況$"),
    re.compile(r"^©JAXA$"),
    re.compile(r"^©Space X$"),
    re.compile(r"^−\s*\d+\s*−$"),
    re.compile(r"^令和 \d+年度以 降$"),
    re.compile(r"^表紙$"),
    re.compile(r"^\d+$"),
    re.compile(r"^（億円）$"),
    re.compile(r"^（実績）$"),
    re.compile(r"^（見通し）$"),
    re.compile(r"^（年度）$"),
    re.compile(r"^（%）$"),
    re.compile(r"^AIRCRAFT, DEFENSE &$"),
    re.compile(r"^SPACE$"),
    re.compile(r"^https?://\S+$"),
    re.compile(r"^出典："),
    re.compile(r"^データ - "),
    re.compile(r"^動画 - "),
    re.compile(r"^コミット済み"),
    re.compile(r"^非静止HTS$"),
    re.compile(r"^静止HTS$"),
    re.compile(r"^従来の静止衛星$"),
]

# Lines that are mostly chart axis labels / isolated numbers.
_CHART_LINE = re.compile(
    r"^[\d,．.%（）\(\)億円実績見通し年度\s\-–—]+$",
)


def _is_vertical_section_noise(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) == 1 and stripped in _VERTICAL_SECTION_CHARS:
        return True
    if len(stripped) <= 2 and all(c in _VERTICAL_SECTION_CHARS or c.isspace() for c in stripped):
        return True
    return False


def _should_join_lines(prev: str, nxt: str) -> bool:
    """Join PDF column-wrap breaks inside Japanese sentences."""
    if not prev or not nxt:
        return False
    if prev.endswith(("。", "！", "？", "」", "）", ":", "：", "—", "…")):
        return False
    if re.match(r"^[\d◦・•\-–—▶]", nxt):
        return False
    if re.match(r"^[\d◦・•\-–—]", prev):
        return False
    if len(nxt) <= 2 and nxt.isdigit():
        return False
    # Short continuation fragment (typical of column wrap).
    if len(nxt) < 20 and not nxt[0].isascii():
        return True
    if len(prev) < 40 and not prev.endswith(("。", "！")):
        return True
    return False


def join_broken_lines(raw: str) -> str:
    lines = raw.splitlines()
    merged: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if merged and merged[-1] != "":
                merged.append("")
            continue
        if merged and merged[-1] != "" and _should_join_lines(merged[-1], stripped):
            merged[-1] = merged[-1] + stripped
        else:
            merged.append(stripped)
    return "\n".join(merged)


def normalize_sections(text: str) -> str:
    """Fix glued headers/footers from PDF text extraction."""
    text = re.sub(r"▶\s*", "\n▶ ", text)
    text = re.sub(r"^表紙(?=\S)", "表紙\n", text, flags=re.MULTILINE)
    text = re.sub(r"事業環境(?=民間|宇宙)", "事業環境\n", text)
    text = re.sub(r"事業の状況(?=民間|防衛)", "事業の状況\n", text)
    text = re.sub(r"基　準(?=内　容)", "基　準\n内　容\n", text)
    text = re.sub(r"FOCUS(?=H3)", "FOCUS\n", text)
    text = re.sub(r"Integrated Report 2023(?=\S)", "Integrated Report 2023\n", text)
    text = re.sub(r"2023宇宙事業", "2023\n宇宙事業", text)
    text = re.sub(r"貢献メディア事業", "貢献\nメディア事業", text)
    text = re.sub(r"必要性(?=また|一方)", "必要性\n", text)
    text = re.sub(r"目的(?=SLIM)", "目的\n", text)
    text = re.sub(r"ミニマムサクセス(?=小型)", "ミニマムサクセス\n", text)
    text = re.sub(r"フルサクセス(?=精度)", "フルサクセス\n", text)
    text = re.sub(r"エクストラサクセス(?=高精度)", "エクストラサクセス\n", text)
    text = re.sub(r"兼ねています(?=太陽)", "兼ねています\n", text)
    for marker in ("©JAXA", "MITSUBISHI HEAVY INDUSTRIES GROUP", "Overview\nMessages"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].strip()
            break
    return text


def clean_text(raw: str) -> str:
    raw = raw.replace("\u00b6", "").replace("¶", "")
    raw = join_broken_lines(raw)
    raw = normalize_sections(raw)

    lines: list[str] = []
    vertical_run = 0
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            vertical_run = 0
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if _is_vertical_section_noise(stripped):
            vertical_run += 1
            if vertical_run >= 3:
                continue
            continue
        vertical_run = 0
        if any(p.match(stripped) for p in NOISE_LINE_PATTERNS):
            continue
        if _CHART_LINE.match(stripped) and len(stripped) < 30:
            continue
        if lines and lines[-1] == stripped:
            continue
        lines.append(stripped)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(spec: ExtractSpec, pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    chunks: list[str] = []
    postprocessors = spec.page_postprocessors or {}
    for page_num in spec.pages:
        if page_num < 1 or page_num > doc.page_count:
            msg = f"Page {page_num} out of range for {pdf_path.name} ({doc.page_count} pages)"
            raise ValueError(msg)
        page_text = doc[page_num - 1].get_text()
        cleaned = clean_text(page_text)
        if page_num in postprocessors:
            cleaned = postprocessors[page_num](cleaned)
        if cleaned:
            chunks.append(f"<!-- source-page: {page_num} -->\n\n{cleaned}")
    return "\n\n---\n\n".join(chunks)


def build_markdown(spec: ExtractSpec, body: str) -> str:
    page_list = ", ".join(str(p) for p in spec.pages)
    return f"""---
doc_id: {spec.doc_id}
title: "{spec.title}"
tier: public
synthetic: false
source_url: "{spec.source_url}"
legacy_file: "public/legacy/{spec.legacy_filename}"
extracted_pages: [{page_list}]
extract_tool: scripts/extract_public_corpus.py
---

# {spec.title}

> 出典: [{spec.source_url}]({spec.source_url})  
> 原本: `public/legacy/{spec.legacy_filename}`（ページ {page_list} を抜粋・整形）

{body}

---

※本ファイルは SafeRoute-RAG デモ用に公開資料から機械抽出した抜粋です。数値・表述は原本 PDF を参照してください。
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        pdf_path = LEGACY_DIR / spec.legacy_filename
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        body = extract_pages(spec, pdf_path)
        out_path = OUTPUT_DIR / spec.output_filename
        out_path.write_text(build_markdown(spec, body), encoding="utf-8")
        char_count = len(body)
        print(f"OK {spec.doc_id}: {out_path.name} ({char_count} chars, {len(spec.pages)} pages)")


if __name__ == "__main__":
    main()
