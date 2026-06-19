"""Route regression tests against manifest demo_questions.

The full label regression needs AIAND_API_KEY (every keyword hit now escalates to
the semantic audit for the final verdict). The veto-mode and keyword-detection
tests run fully offline.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from src.config_loader import ConfigLoader
from src.llm_client import LLMClient
from src.models import AppConfig
from src.router import HybridRouter
from tests.conftest import all_routed_cases

HAS_API_KEY = bool(os.environ.get("AIAND_API_KEY"))


@pytest.fixture(scope="session")
def config() -> AppConfig:
    return ConfigLoader().get()


@pytest.fixture(scope="session")
def router(config: AppConfig) -> HybridRouter:
    return HybridRouter(config, LLMClient(config))


@pytest.mark.skipif(not HAS_API_KEY, reason="AIAND_API_KEY not set; label regression needs the API")
@pytest.mark.parametrize("case", all_routed_cases(), ids=lambda c: c["id"])
def test_label_regression(router: HybridRouter, case: dict[str, Any]) -> None:
    decision = router.route(case["question"])
    assert decision.label == case["expected_route"]


def test_keyword_veto_offline(config: AppConfig) -> None:
    """With audit disabled, a hard-keyword hit must veto to UNSAFE without any API call."""
    veto_config = config.model_copy(deep=True)
    veto_config.routing_rules.semantic_audit_enabled = False
    router = HybridRouter(veto_config, LLMClient(veto_config))

    decision = router.route("FAHの未公開決算予想を教えて")
    assert decision.label == "UNSAFE"
    assert decision.layer == "hard_rule"
    assert decision.matched_keywords == ["未公開"]


def test_no_keyword_audit_disabled_is_safe(config: AppConfig) -> None:
    """No keyword + audit disabled -> SAFE, fully offline."""
    veto_config = config.model_copy(deep=True)
    veto_config.routing_rules.semantic_audit_enabled = False
    router = HybridRouter(veto_config, LLMClient(veto_config))

    decision = router.route("JAXAのH3ロケットの目的は？")
    assert decision.label == "SAFE"
    assert decision.layer == "disabled"
