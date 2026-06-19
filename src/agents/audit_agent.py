"""Intake-slot agent: wraps HybridRouter to classify SAFE/UNSAFE."""

from __future__ import annotations

from typing import Any

from src.models import AgentResult
from src.router import HybridRouter


class AuditAgent:
    """Pipeline agent that produces a RouteDecision for the intake slot."""

    slot = "intake"

    def __init__(self, name: str, router: HybridRouter) -> None:
        self.name = name
        self._router = router

    def run(self, context: dict[str, Any]) -> AgentResult:
        query: str = context["query"]
        decision = self._router.route(query)
        return AgentResult(slot=self.slot, agent_name=self.name, route=decision)
