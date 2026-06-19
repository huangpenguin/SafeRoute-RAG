"""Synthesis-slot agent: assemble retrieved context and generate the final answer."""

from __future__ import annotations

from typing import Any

from src.llm_client import LLMClient
from src.models import AgentResult, RAGConfig, RetrievedChunk, RouteDecision


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into the system-prompt snippet block."""
    parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        src = f" (source: {c.source_url})" if c.source_url else ""
        parts.append(f"[{i}] doc={c.doc_id} score={c.score}{src}\n{c.text}")
    return "\n\n".join(parts) if parts else "（関連スニペットは見つかりませんでした）"


class RagAnswerAgent:
    """Generate the answer on the routed node using the Cookbook system prompt."""

    slot = "synthesis"

    def __init__(self, name: str, llm: LLMClient, rag: RAGConfig) -> None:
        self.name = name
        self._llm = llm
        self._rag = rag

    def run(self, context: dict[str, Any]) -> AgentResult:
        query: str = context["query"]
        route: RouteDecision = context["route"]
        chunks: list[RetrievedChunk] = context.get("chunks", [])
        stream: bool = context.get("stream", False)

        system_prompt = self._rag.generation_system_prompt.format(
            retrieved_chunks=build_context_block(chunks)
        )
        result = self._llm.generate(
            provider_name=route.target_provider,
            system_prompt=system_prompt,
            user_input=query,
            model=route.target_model,
            stream=stream,
        )
        if stream:
            context["answer_stream"] = result
            return AgentResult(slot=self.slot, agent_name=self.name, route=route, chunks=chunks)
        return AgentResult(
            slot=self.slot, agent_name=self.name, route=route, chunks=chunks, answer=str(result)
        )
