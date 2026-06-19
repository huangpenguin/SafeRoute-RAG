"""Local knowledge base: manifest-driven ingest, ruri-small embedding, ChromaDB Top-K."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import chromadb
import numpy as np
import yaml
from chromadb.api import ClientAPI
from sentence_transformers import SentenceTransformer

from src.models import RAGConfig, RetrievedChunk

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCS_DIR = ROOT / "sample_docs"
MANIFEST_PATH = SAMPLE_DOCS_DIR / "manifest.yaml"

# ruri models expect task prefixes for best retrieval quality.
_QUERY_PREFIX = "クエリ: "
_PASSAGE_PREFIX = "文章: "

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Recursive-ish character chunking with overlap (Cookbook ~200-500 chars)."""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        if end == length:
            break
        start = end - overlap
    return chunks


class LocalKnowledgeBase:
    """Ingest sample_docs into ChromaDB and serve Top-K retrieval, 100% locally."""

    def __init__(self, rag: RAGConfig) -> None:
        self._rag = rag
        self._embedder = SentenceTransformer(rag.embedding_model, trust_remote_code=True)
        self._client: ClientAPI = chromadb.PersistentClient(path=str(ROOT / rag.persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=rag.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self._collection.count()

    def _embed_passages(self, texts: list[str]) -> list[list[float]]:
        vectors = self._embedder.encode([_PASSAGE_PREFIX + t for t in texts], normalize_embeddings=True)
        return vectors.tolist()

    def _embed_query(self, text: str) -> list[float]:
        vector = self._embedder.encode([_QUERY_PREFIX + text], normalize_embeddings=True)
        return vector[0].tolist()

    def load_manifest(self) -> dict[str, Any]:
        with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def ingest_manifest(self, reset: bool = True) -> int:
        """Ingest all status=ready documents listed in manifest.yaml. Returns chunk count."""
        manifest = self.load_manifest()
        if reset:
            self._reset_collection()
        total = 0
        for doc in manifest.get("documents", []):
            if doc.get("status") != "ready":
                continue
            path = SAMPLE_DOCS_DIR / doc["path"]
            if not path.exists():
                continue
            total += self._ingest_file(
                path=path,
                doc_id=doc["doc_id"],
                tier=doc.get("tier", "unknown"),
                synthetic=bool(doc.get("synthetic", False)),
                source_url=doc.get("source_url"),
            )
        return total

    def ingest_text(self, text: str, doc_id: str, tier: str = "uploaded", synthetic: bool = False) -> int:
        """Ingest raw text (e.g. uploaded file) into the collection."""
        return self._add_chunks(text, doc_id, tier, synthetic, None)

    def _ingest_file(
        self, path: Path, doc_id: str, tier: str, synthetic: bool, source_url: str | None
    ) -> int:
        raw = path.read_text(encoding="utf-8")
        body = _strip_frontmatter(raw) if path.suffix == ".md" else raw
        return self._add_chunks(body, doc_id, tier, synthetic, source_url)

    def _add_chunks(
        self, body: str, doc_id: str, tier: str, synthetic: bool, source_url: str | None
    ) -> int:
        chunks = _chunk_text(body, self._rag.chunk_size, self._rag.chunk_overlap)
        if not chunks:
            return 0
        embeddings = self._embed_passages(chunks)
        ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
        metadatas: list[dict[str, Any]] = [
            {
                "doc_id": doc_id,
                "tier": tier,
                "synthetic": synthetic,
                "source_url": source_url or "",
            }
            for _ in chunks
        ]
        self._collection.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
        return len(chunks)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        allowed_tiers: set[str] | None = None,
        use_mmr: bool = True,
        mmr_lambda: float = 0.6,
        fetch_multiplier: int = 4,
    ) -> list[RetrievedChunk]:
        """Multi-stage retrieval: over-fetch -> tier filter -> MMR re-rank -> Top-K.

        Args:
            allowed_tiers: if set, drop candidates whose tier is not in this set.
                This is the data-egress guard (e.g. SAFE route -> no confidential).
            use_mmr: apply Maximal Marginal Relevance for relevance/diversity balance.
            mmr_lambda: 1.0 = pure relevance, 0.0 = pure diversity.
        """
        if self._collection.count() == 0:
            return []
        k = top_k or self._rag.top_k
        fetch_k = max(k * fetch_multiplier, k)
        query_vec = np.asarray(self._embed_query(query), dtype=np.float32)

        result = self._collection.query(
            query_embeddings=[query_vec.tolist()],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances", "embeddings"],
        )
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        embs = result.get("embeddings", [[]])[0]

        candidates: list[tuple[RetrievedChunk, np.ndarray]] = []
        for text, meta, dist, emb in zip(docs, metas, dists, embs, strict=False):
            tier = str(meta.get("tier", ""))
            if allowed_tiers is not None and tier not in allowed_tiers:
                continue
            chunk = RetrievedChunk(
                text=text,
                score=round(1.0 - float(dist), 4),
                doc_id=str(meta.get("doc_id", "")),
                tier=tier,
                synthetic=bool(meta.get("synthetic", False)),
                source_url=str(meta.get("source_url") or "") or None,
            )
            candidates.append((chunk, np.asarray(emb, dtype=np.float32)))

        if not candidates:
            return []
        if not use_mmr:
            return [c for c, _ in candidates[:k]]
        return self._mmr_select(query_vec, candidates, k, mmr_lambda)

    @staticmethod
    def _mmr_select(
        query_vec: np.ndarray,
        candidates: list[tuple[RetrievedChunk, np.ndarray]],
        k: int,
        lam: float,
    ) -> list[RetrievedChunk]:
        """Greedy MMR selection over normalized candidate embeddings."""
        chunks = [c for c, _ in candidates]
        mat = np.vstack([e for _, e in candidates])
        rel = mat @ query_vec  # embeddings are L2-normalized -> cosine
        selected: list[int] = []
        remaining = set(range(len(chunks)))
        while remaining and len(selected) < k:
            best_idx, best_score = None, -np.inf
            for i in remaining:
                diversity = max((float(mat[i] @ mat[j]) for j in selected), default=0.0)
                score = lam * float(rel[i]) - (1.0 - lam) * diversity
                if score > best_score:
                    best_idx, best_score = i, score
            assert best_idx is not None
            selected.append(best_idx)
            remaining.discard(best_idx)
        return [chunks[i] for i in selected]

    def _reset_collection(self) -> None:
        self._client.delete_collection(self._rag.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._rag.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
