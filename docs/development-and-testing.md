# Development and testing

## Environment management (uv)

This project uses **[uv](https://docs.astral.sh/uv/)** exclusively.

```bash
uv sync              # install from pyproject.toml + uv.lock
uv sync --dev        # include pytest, ruff
uv add <package>     # add runtime dep
uv add --dev <pkg>   # add dev dep
uv run <command>     # run in project env
```

Do **not** use `pip install`, conda, or poetry directly.

| Task | Command |
| --- | --- |
| Run app | `uv run streamlit run app.py` |
| Rebuild KB | `uv run python scripts/bootstrap_kb.py` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Tests | `uv run pytest` |
| Route eval table | `uv run python scripts/run_route_eval.py --retrieval` |
| Export requirements | `uv export --no-hashes --no-dev -o requirements.txt` |

Commit **`uv.lock`** with code changes so local, CI, and Docker stay aligned.

## Project layout (dev-relevant)

```text
app.py                 Streamlit entry
config/agents.yaml     Hot-reloaded config
src/                   Core library
sample_docs/           Demo corpus + manifest
scripts/               bootstrap_kb, route eval, PDF extract
tests/                 pytest
chroma_db/             Local vector store (gitignored)
```

## Tests

### pytest

```bash
uv run pytest
```

| Suite | Needs API key? |
| --- | --- |
| Hard-rule routing (offline) | No |
| Semantic audit (S01–S12, U07–U12) | Yes (`AIAND_API_KEY` in `.env`) |
| Tier egress guard (`test_retrieval.py`) | No |

### Route regression script

```bash
uv run python scripts/run_route_eval.py            # routing only
uv run python scripts/run_route_eval.py --retrieval  # + expected_docs hit check
```

Writes `eval_results.md` (gitignored). Manifest defines 24 labeled cases; current result **24/24 PASS** with API key.

## CI (GitHub Actions)

`.github/workflows/ci.yml`:

1. **quality** — ruff check + format check (all pushes and PRs)
2. **deploy-hf-space** — push to HF Space on `main` after quality passes (requires `HF_TOKEN` + `HF_SPACE`)

See [deployment.md](deployment.md) for secret setup.

## Extract public PDF corpus (optional)

```bash
uv run --with pymupdf python scripts/extract_public_corpus.py
```

Reads `sample_docs/public/legacy/*.pdf`, writes `sample_docs/public/*.md`. See [gemini-data-collection-prompts.md](gemini-data-collection-prompts.md).

## Common dev issues

| Issue | Fix |
| --- | --- |
| `ruri-small` tokenizer error | Ensure `transformers<5`, `trust_remote_code=True` in `database.py` |
| Empty KB | Run `bootstrap_kb.py` or click manifest ingest in sidebar |
| Two folders under `chroma_db/` | Orphan segments after reset ingest — see [knowledge-base-and-ingest.md](knowledge-base-and-ingest.md) |
| Model 400 from ai& | Update model names in `config/agents.yaml` to match `GET /v1/models` |
