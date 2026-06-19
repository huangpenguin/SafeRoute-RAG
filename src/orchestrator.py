"""Pipeline orchestrator: dispatch intake -> retrieval -> synthesis with hot reload."""

from __future__ import annotations

from typing import Any

from src.agents.audit_agent import AuditAgent
from src.agents.rag_answer_agent import RagAnswerAgent
from src.config_loader import ConfigLoader
from src.database import LocalKnowledgeBase
from src.llm_client import LLMClient
from src.models import AppConfig, RetrievedChunk, RouteDecision
from src.router import HybridRouter


class PipelineResult:
    """Aggregated output of a single pipeline run, consumed by the dashboard."""

    def __init__(
        self,
        route: RouteDecision,
        chunks: list[RetrievedChunk],
        answer: str | None,
        answer_stream: Any | None,
        active: dict[str, str],
    ) -> None:
        self.route = route
        self.chunks = chunks
        self.answer = answer
        self.answer_stream = answer_stream
        self.active = active


class Orchestrator:
    """Read pipeline + active bindings from config and run the slots in order.

    Retrieval is always-local (not an LLM agent). Intake and synthesis are
    hot-swappable via ``active`` in config/agents.yaml.
    """

    def __init__(self, loader: ConfigLoader | None = None, kb: LocalKnowledgeBase | None = None) -> None:
        self._loader = loader or ConfigLoader()
        config = self._loader.get()
        self._llm = LLMClient(config)
        self._router = HybridRouter(config, self._llm)
        self._kb = kb if kb is not None else LocalKnowledgeBase(config.rag)
        self._config = config

    @property
    def kb(self) -> LocalKnowledgeBase:
        return self._kb

    @property
    def config(self) -> AppConfig:
        return self._config

    def _refresh(self) -> None:
        """Reload config if the YAML changed and propagate to sub-components."""
        config = self._loader.get()
        if config is not self._config:
            self._config = config
            self._llm.update_config(config)
            self._router.update_config(config)

    def _build_intake(self) -> AuditAgent:
        name = self._config.active["intake"]
        return AuditAgent(name=name, router=self._router)

    def _build_synthesis(self) -> RagAnswerAgent:
        name = self._config.active["synthesis"]
        return RagAnswerAgent(name=name, llm=self._llm, rag=self._config.rag)

    def run(self, query: str, stream: bool = False) -> PipelineResult:
        """Execute the full pipeline for a user query."""
        self._refresh()
        context: dict[str, Any] = {"query": query, "stream": stream}

        intake_result = self._build_intake().run(context)
        assert intake_result.route is not None
        route = intake_result.route
        context["route"] = route

        # Data-egress guard: a SAFE query routed to the public node must never
        # receive confidential chunks (manifest edge case E02).
        allowed_tiers = None if route.label == "UNSAFE" else {"public", "uploaded"}
        chunks = self._kb.retrieve(query, allowed_tiers=allowed_tiers)
        context["chunks"] = chunks

        synth_result = self._build_synthesis().run(context)
        return PipelineResult(
            route=route,
            chunks=chunks,
            answer=synth_result.answer,
            answer_stream=context.get("answer_stream"),
            active=dict(self._config.active),
        )

    def route_only(self, query: str) -> RouteDecision:
        """Run only the intake routing decision (used by the regression test)."""
        self._refresh()
        result = self._build_intake().run({"query": query})
        assert result.route is not None
        return result.route
