# Architecture

## Problem statement

Enterprise RAG faces a trade-off:

- **Foreign closed models** — strong answers, but confidential text must not be sent abroad.
- **Full on-prem stack** — privacy-friendly, but costly to operate.

SafeRoute-RAG keeps **embedding and retrieval local** (nothing leaves at index/search time for vectors), then routes **generation** to different ai& Inference nodes based on a compliance decision.

## High-level flow

```text
                    ┌─────────────────────────────────────┐
  User (Streamlit)  │  intake: audit_agent               │
        │           │  hard keywords → semantic audit      │
        ▼           │  → RouteDecision SAFE | UNSAFE       │
   HybridRouter     └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  retrieval (always local)            │
                    │  ChromaDB + ruri-small               │
                    │  over-fetch → tier filter → MMR      │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  synthesis: rag_answer_agent         │
                    │  SAFE  → public_node (frontier)      │
                    │  UNSAFE → local_safe_node (domestic) │
                    └─────────────────────────────────────┘
```

Aligned with [ai& Cookbook — Chat over Documents (RAG)](https://docs.aiand.com/cookbook/rag/) **Approach B**: local embedding + Top-K + OpenAI-compatible chat completion.

## Two-layer router

| Layer | Mechanism | Output |
| --- | --- | --- |
| **1 — Hard keywords** | Substring match on `routing_rules.hard_keywords` | Strong suspicion (not always final) |
| **2 — Semantic audit** | Structured JSON verdict via ai& (`label`, `reason`, `confidence`) | Final `SAFE` or `UNSAFE` |

Default policy (`hard_keyword_escalates: true`): keyword hits **escalate** to layer 2 instead of an immediate veto. That avoids false positives such as “public IR that mentions 財務報表”. Set `hard_keyword_escalates: false` to restore instant keyword veto.

Implementation: `src/router.py`, `src/agents/audit_agent.py`.

## Data egress guard

When route is `SAFE`, retrieval uses `allowed_tiers={public, uploaded}` so **confidential** chunks never reach the public node — even if vector search would have ranked them highly (manifest edge case E02).

When route is `UNSAFE`, all tiers are searchable; generation stays on the domestic node.

Implementation: `src/orchestrator.py`.

## Multi-stage retrieval

1. Over-fetch (`top_k × 4` candidates)
2. Tier filter (if SAFE)
3. MMR re-ranking (relevance vs diversity)
4. Top-K to the generator

Implementation: `src/database.py`.

## Multi-agent pipeline (YAML hot-swap)

```yaml
pipeline: [intake, retrieval, synthesis]
active:
  intake: audit_agent
  synthesis: rag_answer_agent
```

| Slot | Default agent | Role |
| --- | --- | --- |
| `intake` | `audit_agent` | Route SAFE/UNSAFE |
| `retrieval` | (fixed local code) | ChromaDB + embedding |
| `synthesis` | `rag_answer_agent` | Context + streamed answer |

Change `active.*` in `config/agents.yaml` without code changes to swap agents (e.g. future `image_brief_agent` / `image_qa_agent`).

Orchestrator: `src/orchestrator.py`.

## RAG generation constraint

The system prompt requires answers **only from retrieved snippets**. Off-topic or general-knowledge questions still route (often `SAFE`) but the model will say the snippets do not contain an answer — this is intentional for the contest demo, not a general chatbot.

## Module map

| Path | Responsibility |
| --- | --- |
| `app.py` | Streamlit UI, sidebar ingest, routing dashboard |
| `src/orchestrator.py` | Pipeline dispatch |
| `src/router.py` | HybridRouter |
| `src/database.py` | LocalKnowledgeBase, ChromaDB |
| `src/llm_client.py` | Per-provider OpenAI clients (ai&) |
| `src/agents/` | Pluggable slot agents |
| `config/agents.yaml` | Providers, routing, RAG, active bindings |
