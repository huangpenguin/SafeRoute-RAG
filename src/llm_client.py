"""Dynamic OpenAI-compatible client factory for ai& / OpenAI nodes."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema

from src.config_loader import resolve_api_key
from src.models import AppConfig, AuditVerdict, ProviderConfig

_AUDIT_JSON_SCHEMA = {
    "name": "audit_verdict",
    "schema": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": ["SAFE", "UNSAFE"]},
            "reason": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["label", "reason", "confidence"],
        "additionalProperties": False,
    },
}


class LLMClient:
    """Build and cache one OpenAI client per provider, as in the ai& Cookbook.

    Each provider gets an independent ``OpenAI(base_url=..., api_key=...)`` so that
    public_node and local_safe_node can point at completely different endpoints.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._clients: dict[str, OpenAI] = {}

    def update_config(self, config: AppConfig) -> None:
        """Swap in a reloaded config and reset cached clients."""
        self._config = config
        self._clients.clear()

    def _provider(self, name: str) -> ProviderConfig:
        try:
            return self._config.providers[name]
        except KeyError as exc:
            raise KeyError(f"Unknown provider '{name}' in config.providers") from exc

    def _client(self, provider_name: str) -> OpenAI:
        if provider_name not in self._clients:
            provider = self._provider(provider_name)
            self._clients[provider_name] = OpenAI(
                base_url=provider.base_url,
                api_key=resolve_api_key(provider),
            )
        return self._clients[provider_name]

    def audit(self, provider_name: str, system_prompt: str, user_input: str, model: str | None = None) -> AuditVerdict:
        """Run the semantic-audit classifier with Structured Outputs (JSON verdict)."""
        provider = self._provider(provider_name)
        audit_model = model or provider.audit_model or provider.default_model
        resp = self._client(provider_name).chat.completions.create(
            model=audit_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.0,
            max_tokens=200,
            response_format=ResponseFormatJSONSchema(
                type="json_schema",
                json_schema=cast(Any, _AUDIT_JSON_SCHEMA),
            ),
        )
        raw = (resp.choices[0].message.content or "").strip()
        return AuditVerdict.model_validate_json(raw)

    def generate(
        self,
        provider_name: str,
        system_prompt: str,
        user_input: str,
        model: str | None = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """Generate the final RAG answer on the routed node."""
        provider = self._provider(provider_name)
        gen_model = model or provider.default_model
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        if stream:
            return self._stream(provider_name, gen_model, messages)
        resp = self._client(provider_name).chat.completions.create(
            model=gen_model,
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    def _stream(self, provider_name: str, model: str, messages: list[ChatCompletionMessageParam]) -> Iterator[str]:
        stream = self._client(provider_name).chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
