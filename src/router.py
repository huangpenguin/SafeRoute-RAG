"""HybridRouter: layer-1 hard keyword rules + layer-2 LLM semantic audit."""

from __future__ import annotations

import time

from src.llm_client import LLMClient
from src.models import AppConfig, AuditVerdict, RouteDecision, RouteLabel, RouteLayer


class HybridRouter:
    """Decide SAFE/UNSAFE for a user query and bind it to a target provider."""

    def __init__(self, config: AppConfig, llm: LLMClient) -> None:
        self._config = config
        self._llm = llm

    def update_config(self, config: AppConfig) -> None:
        self._config = config

    def _target(self, label: RouteLabel) -> tuple[str, str]:
        """Resolve (provider, model) for the synthesis agent given a route label."""
        agent_name = self._config.active["synthesis"]
        agent = self._config.agents[agent_name]
        bind = agent.route_bind or {}
        provider_name = bind.get(label) or next(iter(self._config.providers))
        provider = self._config.providers[provider_name]
        return provider_name, provider.default_model

    def route(self, user_input: str) -> RouteDecision:
        """Run both layers and return a fully-populated RouteDecision.

        Layer 1 (hard keywords) flags suspicion. Depending on config it either
        vetoes immediately to UNSAFE, or escalates to the layer-2 semantic audit
        which makes the final call (false-positive avoidance). When audit is
        disabled, layer 1 is the sole decision maker.
        """
        start = time.perf_counter()
        rules = self._config.routing_rules
        matched = [kw for kw in rules.hard_keywords if kw in user_input]

        veto = bool(matched) and (not rules.hard_keyword_escalates or not rules.semantic_audit_enabled)
        if veto:
            return self._finalize(
                "UNSAFE", "hard_rule", start, matched_keywords=matched,
                reason="hard keyword veto",
            )

        if not rules.semantic_audit_enabled:
            return self._finalize("SAFE", "disabled", start)

        verdict = self._run_audit(user_input, matched, rules.audit_system_prompt)
        return self._finalize(
            verdict.label,
            "semantic_audit",
            start,
            matched_keywords=matched,
            audit_raw=verdict.model_dump_json(),
            reason=verdict.reason,
            confidence=verdict.confidence,
        )

    def _run_audit(self, user_input: str, matched: list[str], base_prompt: str) -> AuditVerdict:
        """Call the audit agent, injecting matched keywords as a non-decisive prior."""
        audit_agent = self._config.agents[self._config.active["intake"]]
        prompt = base_prompt
        if matched:
            prompt = (
                base_prompt
                + f"\n\n参考情報：入力には注意キーワード（{', '.join(matched)}）が含まれます。"
                + "ただしキーワードの有無だけで判断せず、公開情報を求めているか、"
                + "社内機密・未公開情報を引き出そうとしているかで最終判断してください。"
            )
        return self._llm.audit(
            provider_name=audit_agent.provider or "local_safe_node",
            system_prompt=prompt,
            user_input=user_input,
            model=audit_agent.model,
        )

    def _finalize(
        self,
        label: RouteLabel,
        layer: RouteLayer,
        start: float,
        matched_keywords: list[str] | None = None,
        audit_raw: str | None = None,
        reason: str | None = None,
        confidence: float | None = None,
    ) -> RouteDecision:
        provider, model = self._target(label)
        return RouteDecision(
            label=label,
            layer=layer,
            matched_keywords=matched_keywords or [],
            audit_raw=audit_raw,
            reason=reason,
            confidence=confidence,
            target_provider=provider,
            target_model=model,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )
