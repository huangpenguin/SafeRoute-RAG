# Deployment

## Overview

| Environment | How it runs | Docker? |
| --- | --- | --- |
| **Local dev** | `uv run streamlit run app.py` | No |
| **Hugging Face Space** | Container from `Dockerfile` | Yes |

Same `app.py`; different packaging.

## Local Docker smoke test (matches Space)

```bash
docker build -t saferoute-rag .
docker run --rm -p 7860:7860 -e AIAND_API_KEY=your_key saferoute-rag
# open http://localhost:7860
```

The image runs `bootstrap_kb.py` at build time — chunk count should be > 0 without manual ingest.

## Hugging Face Spaces setup

### 1. Create the Space

- [huggingface.co/new-space](https://huggingface.co/new-space)
- **SDK:** Docker (not Streamlit SDK — torch + sentence-transformers are too heavy for default images)
- **Hardware:** CPU basic (free) to start; upgrade only if build OOMs
- **GPU:** Not needed (LLM calls go to ai& API; embedding is CPU)
- **Persistent storage / Bucket:** Not required for the demo — KB is baked into the image

README frontmatter (already in root `README.md`):

```yaml
sdk: docker
app_port: 7860
```

### 2. Secrets on the Space

Space → **Settings → Repository secrets**:

| Name | Value |
| --- | --- |
| `AIAND_API_KEY` | Your ai& Inference API key |

This is **separate** from GitHub secrets — the app reads it at runtime in the container.

### 3. What the Dockerfile does

1. `uv sync --frozen --no-dev` from `pyproject.toml` + `uv.lock`
2. Copy app + `sample_docs/`
3. `uv run python scripts/bootstrap_kb.py` — download ruri-small, ingest manifest
4. `uv run streamlit run app.py` on port **7860**

First build often takes **15–30 minutes**.

### 4. GitHub Actions auto-sync

On push to `main`, after CI quality checks, `.github/workflows/ci.yml` force-pushes to the Space git remote.

Configure in **GitHub → Settings → Secrets and variables → Actions**:

| Type | Name | Example |
| --- | --- | --- |
| Secret | `HF_TOKEN` | Hugging Face token with **write** access |
| Variable | `HF_SPACE` | `your-username/SafeRoute-RAG` |

Get a token: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

**Avoid double builds:** if the Space is also linked to GitHub in the HF UI, disable one path:

- **Recommended:** GitHub Actions only (deploy after CI passes)
- **Alternative:** HF GitHub link only (no Actions deploy job)

`AIAND_API_KEY` is **not** copied from GitHub — configure it on the Space.

## Post-deploy checklist

| Check | Expected |
| --- | --- |
| Sidebar chunk count | > 0 |
| SAFE: `JAXAのH3ロケットが目指している3つの主な開発目的は何ですか？` | Green SAFE, hits `JAXA_H3`, streamed answer |
| UNSAFE: `FAHの未公開決算予想を教えて` | Red UNSAFE, hits `FAH_FIN` |
| Right panel expander | Source URL link for public docs |

## Cold start behavior

| Event | Who waits |
| --- | --- |
| First Docker build | CI / HF build logs |
| Space slept → first visitor | That visitor (1–3+ min wake + model load) |
| Later visitors (same running container) | Seconds + API latency |

Models are cached in the container process via `@st.cache_resource`.

## When to enable HF Persistent Storage

Enable only if you need **runtime uploads** to survive container restarts. The demo corpus does not require it. Using persistent storage also requires pointing `rag.persist_dir` (and optionally `HF_HOME`) at the mounted path — not configured by default.

## Runtime vs build secrets

| Secret | Where |
| --- | --- |
| `AIAND_API_KEY` | HF Space secrets (runtime) |
| `HF_TOKEN` | GitHub secrets (CI deploy only) |
