# SafeRoute-RAG — Current Plan

## Corpus status (2026-06-16)

- **10/10 documents ready** in manifest (4 confidential + 6 public MD)
- Legacy PDFs: `sample_docs/public/legacy/`
- Extracted MD: `sample_docs/public/*.md` via `scripts/extract_public_corpus.py`

## Architecture focus

1. **RAG**: ai& Cookbook Approach B (local embedding + Top-K + ai& generation)
2. **Multi-agent**: Pipeline slots (`intake`, `retrieval`, `synthesis`) + YAML `active` agent binding
3. **MVP agents**: `audit_agent`, `rag_answer_agent` — image agents documented as future slot swaps

## Next implementation step

Scaffold → `config/agents.yaml` → orchestrator → agents → Streamlit app

See `.cursor/plans/saferoute-rag_798dfb1f.plan.md` and `.cursor/project-context/decisions.md`.
