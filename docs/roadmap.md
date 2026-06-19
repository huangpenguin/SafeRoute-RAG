# Roadmap

Planned improvements and explicit non-goals for the Qiita ai& Inference contest demo and beyond.

## Shipped (MVP)

- [x] Local Japanese embedding (`cl-nagoya/ruri-small`) + ChromaDB
- [x] Two-layer router with structured audit JSON (`label`, `reason`, `confidence`)
- [x] Keyword escalation (false-positive safe cases S07–S12)
- [x] Tier-aware retrieval egress guard (SAFE never sees confidential chunks)
- [x] MMR re-ranking over over-fetched candidates
- [x] YAML hot-swappable pipeline slots (`intake`, `synthesis`)
- [x] Streamlit chat + routing dashboard + streaming answers
- [x] Sidebar source URLs in retrieval expanders
- [x] Docker + HF Spaces + GitHub Actions deploy
- [x] 24/24 manifest route regression

## Near term (high value for demo / article)

### In-chat citations

Today: sources appear in the **right-panel expander** and in the LLM context block, not as footnotes in the assistant message.

**Plan:** render `[1] doc_id` footnotes under the streamed answer with links to `source_url`.

### KB-scope intent

Today: every question runs full RAG; off-topic queries get “not in snippets” answers even on `SAFE` route.

**Plan (pick one or combine):**

- **LLM triage:** `in_kb_rag` | `out_of_kb_chat` | `confidential`
- **Score threshold:** if top retrieval score < τ, switch to general chat on public node (still SAFE)

### Demo UX on Space

- Example question buttons (SAFE / UNSAFE / false-positive)
- Disclaimer that FAH confidential docs are synthetic
- Fill in live Space URL in README after deploy

## Phase 2 (article “future work”)

### Tool-calling / agentic RAG

Use [ai& tool calling](https://docs.aiand.com/capabilities/tool-calling/) so the model decides when to retrieve or re-query — useful for multi-hop questions. Heavier than current fixed pipeline; not required for contest MVP.

### Structured outputs for answers

Optional chunk-ID citations via [structured outputs](https://docs.aiand.com/capabilities/streaming/) — align with Cookbook “scaling up” ideas.

### Multimodal slot swap (same orchestrator)

Documented slot contract; not implemented:

| Slot | Swap in |
| --- | --- |
| `intake` | `image_brief_agent` (text → image prompt) |
| `synthesis` | `image_qa_agent` (vision QA) |

Narrative: one YAML, switch from compliance RAG to generate-and-review pipeline.

### HF Persistent Storage

Only if audience uploads must survive restarts — mount path + config change for `persist_dir`.

## Non-goals (contest scope)

- LangChain / LlamaIndex agent executors
- Real OpenAI vs ai& A/B benchmarking (single ai& key for now)
- Re-ranking with cross-encoder (Cookbook scaling — out of MVP)
- Production multi-tenant ACL / per-user collections
- PDF upload in Streamlit UI (only `.md` / `.txt` today)

## Contest timeline reminder

Qiita ai& Inference submission deadline: check [official event page](https://qiita.com/official-events/750d1f37b7217167b1ad). Prioritize live Space + article GIF over phase-2 features.
