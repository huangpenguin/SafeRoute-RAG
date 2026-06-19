"""Agent protocol shared by all pipeline slots."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from src.models import AgentResult


@runtime_checkable
class AgentProtocol(Protocol):
    """Every pluggable agent implements run(context) -> AgentResult."""

    name: str
    slot: str

    def run(self, context: dict[str, Any]) -> AgentResult:
        """Execute this agent's slot using the shared pipeline context."""
        ...
