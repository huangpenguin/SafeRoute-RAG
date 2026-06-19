# Architecture Decisions

## ADR-001: Corpus pipeline (legacy PDF → extracted MD)

- Raw downloads live in `sample_docs/public/legacy/` (immutable originals).
- RAG ingests **extracted** `sample_docs/public/*.md` only, not full IR PDFs.
- Extraction: `uv run --with pymupdf python scripts/extract_public_corpus.py`
- Page selection is keyword/section curated per doc in the script (`ExtractSpec.pages`).
- `manifest.yaml` tracks `legacy_path`, `path` (MD), `extracted_pages`, `status`.

## ADR-002: Multi-agent — MVP vs vision

### User vision

YAML hot-swappable **agents** in a pipeline, e.g.:

- Slot A: dialogue/summary **or** image generation
- Slot B: RAG synthesis **or** image quality review

### Current plan gap (before implementation)

Original `plan.md` says "Agent 热插拔" but early module design only has:

- `router.py` — hard rules + semantic audit (one fixed role)
- `llm_client.py` — provider/model switch by SAFE/UNSAFE (not agent abstraction)

So **multi-agent is a narrative goal, not yet reflected in code structure**. Only **multi-provider / multi-model** hot-swap is designed.

### Decision: slot-based agent registry (implement in MVP config shape)

Treat an **agent** as: `{role, provider, model, system_prompt, tools?, enabled}` registered in `config/agents.yaml`.

**MVP pipeline (RAG demo — 3 agents, 2 slots):**

| Slot | Default agent | Role | Swappable to (future) |
|------|---------------|------|------------------------|
| `intake` | `audit_agent` | Route SAFE/UNSAFE | `requirement_agent`, `image_brief_agent` |
| `synthesis` | `rag_answer_agent` | Context + answer | `image_qa_agent`, `compliance_review_agent` |

Always-local (not an LLM agent): `retrieval` step = ChromaDB + local embedding.

**Implementation sketch:**

```
config/agents.yaml
  pipeline: [intake, retrieval, synthesis]
  agents:
    audit_agent: { slot: intake, type: llm_classifier, ... }
    rag_answer_agent: { slot: synthesis, type: llm_rag, route_bind: {SAFE: public_node, UNSAFE: local_safe_node} }
  active:
    intake: audit_agent
    synthesis: rag_answer_agent
```

`src/orchestrator.py` (new): reads pipeline + active agents, dispatches slots. Changing `active.intake` in YAML hot-reloads without Streamlit restart.

**Future multimodal demo (same slots, different agents):**

```yaml
active:
  intake: image_brief_agent      # text → image prompt
  synthesis: image_qa_agent      # vision model scores output
```

Retrieval slot can be `noop` or a asset store when not RAG.

### What NOT to do for contest deadline

- Do not adopt LangChain AgentExecutor / LlamaIndex agents — keeps story clear.
- Do not implement image agents in MVP unless time allows; **document the slot contract** in README for Qiita.

## ADR-003: RAG aligned with ai& Cookbook

- Primary: Approach B (local embedding + Top-K + ai& chat completion).
- System prompt pattern from cookbook: answer only from snippets.
- Models: `qwen/qwen3.5-9b` (audit/prototype), `qwen/qwen3.5-27b` or `openai/gpt-oss-120b` (generation).

## ADR-005: Routing policy — escalate, not veto (implemented)

- ai& real model catalog differs from plan: use `openai/gpt-oss-120b` (public),
  `qwen/qwen3.6-27b` (local_safe generation), `deepseek-ai/deepseek-v4-flash` (audit).
- Hard keyword hit is a **strong prior**, escalated to layer-2 semantic audit for the
  final verdict (`hard_keyword_escalates: true`). Pure veto kept as opt-out fallback.
  Reason: manifest S07–S12 (公開IRに敏感語) vs U01–U06 share keywords → only semantics
  can separate them. Result: 24/24 demo_questions pass.
- Audit uses **Structured Outputs** (`response_format=json_schema`) → `AuditVerdict
  {label, reason, confidence}`; dashboard shows reason/confidence.

## ADR-006: Multi-stage retrieval + data-egress guard (implemented)

- `LocalKnowledgeBase.retrieve`: over-fetch (×4) → tier filter → MMR re-rank → Top-K.
- **Egress guard**: SAFE route passes `allowed_tiers={public, uploaded}` so confidential
  chunks are never sent to the public node (fixes manifest E02). UNSAFE allows all tiers.
- Streamlit uses SSE streaming (`st.write_stream`).

## ADR-004: Embedding model

- Japanese corpus: `cl-nagoya/ruri-small` (not cookbook's English `bge-small-en-v1.5`).
