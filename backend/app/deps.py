"""Dependency providers for TrendPulse local FastAPI routes."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import PUBLIC_DATA_DIR, Settings, get_settings


def get_app_settings() -> Settings:
    """Return current cached settings."""
    return get_settings()


@lru_cache(maxsize=1)
def get_public_data_dir() -> Path:
    """Return directory containing static JSON snapshots (`latest.json`, `history.json`, `archive/`)."""
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return PUBLIC_DATA_DIR
