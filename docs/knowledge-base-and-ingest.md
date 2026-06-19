# Knowledge base and ingest

## Two layers: source files vs vector store

| Layer | Location | Role |
| --- | --- | --- |
| **Source corpus** | `sample_docs/` + `manifest.yaml` | Raw Markdown, catalog, demo test questions |
| **Vector store** | `./chroma_db/` | Chunks, embeddings, metadata (ChromaDB) |

**Search uses ChromaDB only** — not the Markdown files directly.

```
sample_docs/*.md  ──ingest──►  chroma_db/  ──retrieve──►  RAG
```

## manifest.yaml

Index and test spec (not ingested as a document itself):

- Which files to ingest (`status: ready`)
- `doc_id`, `tier` (`public` | `confidential`), `source_url`
- Structured `demo_questions` for route regression (24 cases, 24/24 pass)

Public docs: extracted MD under `sample_docs/public/` (from legacy PDFs via `scripts/extract_public_corpus.py`).  
Confidential docs: synthetic FAH Markdown under `sample_docs/confidential/` (demo only).

## How ingest works

1. Read `manifest.yaml` → documents with `status: ready`
2. Load each file under `sample_docs/`
3. Strip YAML frontmatter for `.md`
4. Chunk (`500` chars, `50` overlap)
5. Embed with local `ruri-small` (prefix `文章:` / `クエリ:`)
6. Upsert into Chroma collection `saferoute`

Code: `src/database.py` → `ingest_manifest()`, `ingest_text()`.

## UI buttons (`app.py`)

| Control | Behavior |
| --- | --- |
| **manifest を一括取り込み** | `ingest_manifest(reset=True)` — **deletes** collection, re-imports all manifest docs |
| **アップロードを取り込み** | `ingest_text()` — append upload; does **not** reset; tier=`uploaded` |

Upload does **not** auto-run on file select — user must click the ingest button.

## Auto-ingest on startup

If `chroma_db` is empty when Streamlit starts, `get_orchestrator()` runs `ingest_manifest(reset=False)`.

Docker build runs `scripts/bootstrap_kb.py` (`reset=True`) so the image ships with a ready KB.

## Do you need both sample_docs and chroma_db in Git?

| Scenario | `sample_docs/` | `chroma_db/` |
| --- | --- | --- |
| Local dev after first ingest | Yes (source) | Generated locally (gitignored) |
| HF Docker build (current) | **Yes** (build reads it) | Built inside image (not committed) |
| Q&A at runtime | Not read | **Yes** |

You do **not** commit `chroma_db/` — the Dockerfile builds it from `sample_docs/`.

## ChromaDB on disk

Typical layout:

```text
chroma_db/
├── chroma.sqlite3          # metadata, collection mapping
└── <uuid>/                 # segment (HNSW index files)
```

Multiple UUID folders can appear after **`reset=True` re-ingest** — old segments may remain as orphaned directories while only one collection is active. To clean:

```bash
rm -rf chroma_db/
uv run python scripts/bootstrap_kb.py
```

Check active size: sidebar **登録チャンク数** (~70 for the demo corpus).

## Retrieval metadata

Each chunk stores: `doc_id`, `tier`, `synthetic`, `source_url`.  
The dashboard expander shows `doc_id`, score, tier, snippet text, and **source URL** for public docs.  
The chat answer itself does not yet include inline citations (see [roadmap.md](roadmap.md)).

## Enterprise comparison

Production systems usually separate object storage (raw files), an ingest pipeline (workers/queues), and a managed vector DB (pgvector, Pinecone, etc.). This demo colocates Chroma on disk for simplicity — adequate for Qiita, not a production pattern.
