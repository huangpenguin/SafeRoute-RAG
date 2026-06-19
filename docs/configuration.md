# Configuration

All runtime tuning is in **`config/agents.yaml`**. `src/config_loader.py` reloads on file mtime change (no Streamlit restart).

## Environment variables

Secrets are **never** stored in YAML — only env var names.

| Variable | Required | Used by |
| --- | --- | --- |
| `AIAND_API_KEY` | Yes (local + Space) | All ai& nodes in the demo |
| `OPENAI_API_KEY` | No | Only if `public_node` points to real OpenAI |

**Local:** copy `.env.example` → `.env`.

**Hugging Face Space:** Settings → Repository secrets → `AIAND_API_KEY`.

Missing keys raise an explicit error (no silent fallback).

## Provider nodes

Each node is an independent `OpenAI(base_url=..., api_key=...)` client.

| Node | Role | Default model (ai& catalog) |
| --- | --- | --- |
| `public_node` | SAFE generation (plays “frontier public”) | `openai/gpt-oss-120b` |
| `local_safe_node` | UNSAFE generation (domestic) | `qwen/qwen3.6-27b` |
| `local_safe_node.audit_model` | Layer-2 semantic audit | `deepseek-ai/deepseek-v4-flash` |

Model IDs must exist on your ai& account (`GET /v1/models`). Update `config/agents.yaml` if the catalog changes.

## Routing rules

| Key | Default | Meaning |
| --- | --- | --- |
| `hard_keywords` | 社内機密, 未公開, … | Layer-1 substring triggers |
| `semantic_audit_enabled` | `true` | Enable layer-2 LLM audit |
| `hard_keyword_escalates` | `true` | Keywords → audit; `false` → instant UNSAFE |
| `audit_system_prompt` | (Japanese) | Compliance auditor instructions |

## RAG settings

| Key | Default |
| --- | --- |
| `embedding_model` | `cl-nagoya/ruri-small` |
| `chunk_size` / `chunk_overlap` | `500` / `50` |
| `top_k` | `4` |
| `collection_name` | `saferoute` |
| `persist_dir` | `./chroma_db` |
| `generation_system_prompt` | Answer only from `{retrieved_chunks}` |

Requires `trust_remote_code=True` for ruri (line-distilbert tokenizer). Japanese deps: `fugashi`, `unidic-lite`, `sentencepiece`.

## Agent registry

```yaml
agents:
  audit_agent:
    slot: intake
    provider: local_safe_node
    model: deepseek-ai/deepseek-v4-flash
  rag_answer_agent:
    slot: synthesis
    route_bind:
      SAFE: public_node
      UNSAFE: local_safe_node

active:
  intake: audit_agent
  synthesis: rag_answer_agent
```

## Dependency versions

Managed with **uv** in `pyproject.toml` + `uv.lock`. Notable pins:

- `transformers>=4.40,<5` (v5 breaks ruri-small)
- `sentence-transformers>=2.7,<4`

Export for legacy pip-only flows: `uv export --no-hashes --no-dev -o requirements.txt`.
