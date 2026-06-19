"""YAML config loader with mtime-based hot reload and env-based secret resolution."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.models import AppConfig, ProviderConfig

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "config" / "agents.yaml"


class ConfigLoader:
    """Load and cache AppConfig, reloading when the YAML file changes on disk."""

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG_PATH) -> None:
        self._path = Path(config_path)
        self._cached: AppConfig | None = None
        self._mtime: float | None = None

    def get(self) -> AppConfig:
        """Return the current config, reloading if the file's mtime changed."""
        mtime = self._path.stat().st_mtime
        if self._cached is None or mtime != self._mtime:
            self._cached = self._load()
            self._mtime = mtime
        return self._cached

    def _load(self) -> AppConfig:
        with self._path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return AppConfig.model_validate(raw)


def resolve_api_key(provider: ProviderConfig) -> str:
    """Resolve a provider's API key from its env var; raise if missing (no silent fallback)."""
    key = os.environ.get(provider.api_key_env)
    if not key:
        raise RuntimeError(
            f"Missing API key: set environment variable '{provider.api_key_env}' "
            f"for provider '{provider.name}'. Copy .env.example to .env and fill it in."
        )
    return key
