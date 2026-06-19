# SafeRoute-RAG Documentation

English reference for architecture, operations, and development. The root [README](../README.md) stays short: overview, quick start, and links here.

## Guides

| Document | Contents |
| --- | --- |
| [architecture.md](architecture.md) | Pipeline slots, two-layer router, RAG flow, multi-agent YAML |
| [configuration.md](configuration.md) | `config/agents.yaml`, environment variables, model nodes |
| [knowledge-base-and-ingest.md](knowledge-base-and-ingest.md) | `sample_docs/` vs `chroma_db/`, manifest, ingest buttons, Chroma layout |
| [deployment.md](deployment.md) | Local Docker, Hugging Face Spaces, hardware, CI auto-sync |
| [development-and-testing.md](development-and-testing.md) | uv workflow, pytest, route regression, CI |
| [roadmap.md](roadmap.md) | Planned features and non-goals |

## Supplementary

| Document | Contents |
| --- | --- |
| [gemini-data-collection-prompts.md](gemini-data-collection-prompts.md) | Prompts to build the Japanese aerospace/defense demo corpus |
| [packs/](packs/) | Template pack notes (CI / Python quality) |

## Internal agent notes

Stable decisions for contributors using Cursor: [.cursor/project-context/decisions.md](../.cursor/project-context/decisions.md).
