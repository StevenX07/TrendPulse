"""Application settings and safe `.env` persistence for TrendPulse."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
PUBLIC_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"


class Settings(BaseSettings):
    """Runtime settings loaded cleanly from `.env` (gitignored)."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    apify_api_token: str = Field(default="", alias="APIFY_API_TOKEN")
    apify_max_charge_per_run_usd: float = Field(
        default=1.05,
        alias="APIFY_MAX_CHARGE_PER_RUN_USD",
    )
    default_region: str = Field(default="GLOBAL", alias="DEFAULT_REGION")


def mask_secret(value: str) -> str:
    """Mask API tokens while keeping prefix/suffix recognizable."""
    clean = (value or "").strip()
    if not clean:
        return ""
    if len(clean) <= 10:
        return "*" * len(clean)
    return f"{clean[:6]}...{clean[-4:]}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


def reload_settings() -> Settings:
    """Clear settings cache and reload from `.env`."""
    get_settings.cache_clear()
    return get_settings()


def write_env_updates(updates: Dict[str, str]) -> Settings:
    """Safely update `.env` values without dropping unrelated entries."""
    existing_lines: List[str] = []
    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    new_lines: List[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key, _ = line.split("=", 1)
        key = key.strip()
        if key in remaining:
            val = remaining.pop(key).replace("\n", "").replace("\r", "").strip()
            new_lines.append(f"{key}={val}")
        else:
            new_lines.append(line)

    for key, val in remaining.items():
        clean_val = val.replace("\n", "").replace("\r", "").strip()
        new_lines.append(f"{key}={clean_val}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return reload_settings()
