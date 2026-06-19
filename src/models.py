"""Pydantic models for configuration, routing decisions, and agent results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RouteLabel = Literal["SAFE", "UNSAFE"]
RouteLayer = Literal["hard_rule", "semantic_audit", "disabled"]


class ProviderConfig(BaseModel):
    """A single OpenAI-compatible inference node (ai& or real OpenAI)."""

    name: str
    base_url: str
    api_key_env: str = Field(description="Environment variable name holding the API key.")
    default_model: str
    audit_model: str | None = None


class RoutingRules(BaseModel):
    """Two-layer router configuration."""

    hard_keywords: list[str] = Field(default_factory=list)
    semantic_audit_enabled: bool = True
    # When True, a hard-keyword hit is treated as a strong prior and escalated to
    # the semantic audit for the final verdict (enables false-positive avoidance).
    # When False, a hard-keyword hit is an immediate UNSAFE veto.
    hard_keyword_escalates: bool = True
    audit_system_prompt: str


class AuditVerdict(BaseModel):
    """Structured output of the semantic audit (ai& Structured Outputs)."""

    label: RouteLabel
    reason: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RAGConfig(BaseModel):
    """Local retrieval / embedding configuration (Cookbook Approach B)."""

    embedding_model: str = "cl-nagoya/ruri-small"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4
    collection_name: str = "saferoute"
    persist_dir: str = "./chroma_db"
    generation_system_prompt: str


class AgentSpec(BaseModel):
    """Registry entry for a pipeline agent."""

    slot: Literal["intake", "retrieval", "synthesis"]
    type: str
    provider: str | None = None
    model: str | None = None
    route_bind: dict[RouteLabel, str] | None = None


class AppConfig(BaseModel):
    """Top-level configuration parsed from config/agents.yaml."""

    pipeline: list[str]
    providers: dict[str, ProviderConfig]
    routing_rules: RoutingRules
    rag: RAGConfig
    agents: dict[str, AgentSpec]
    active: dict[str, str]


class RouteDecision(BaseModel):
    """Result of HybridRouter.route(); consumed directly by the dashboard."""

    label: RouteLabel
    layer: RouteLayer
    matched_keywords: list[str] = Field(default_factory=list)
    audit_raw: str | None = None
    reason: str | None = None
    confidence: float | None = None
    target_provider: str
    target_model: str
    latency_ms: float = 0.0


class RetrievedChunk(BaseModel):
    """A single Top-K retrieval hit with metadata for the dashboard."""

    text: str
    score: float
    doc_id: str
    tier: str
    synthetic: bool
    source_url: str | None = None


class AgentResult(BaseModel):
    """Generic result passed between pipeline slots."""

    slot: str
    agent_name: str
    route: RouteDecision | None = None
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    answer: str | None = None
