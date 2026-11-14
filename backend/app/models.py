"""Pydantic request/response schemas for TrendPulse local API."""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class CollectRequest(BaseModel):
    """Trigger a local weekly snapshot collection."""

    mode: Literal["free", "full"] = "free"
    max_apify_usd: Optional[float] = Field(default=None, ge=0.05, le=3.0)


class SettingsResponse(BaseModel):
    """Safe settings snapshot (masks secret tokens)."""

    apify_configured: bool
    apify_token_masked: str = ""
    apify_max_charge_per_run_usd: float
    default_region: str


class SettingsUpdateRequest(BaseModel):
    """Partial `.env` update from local Settings modal."""

    apify_api_token: Optional[str] = None
    apify_max_charge_per_run_usd: Optional[float] = Field(default=None, ge=0.05, le=3.0)
    default_region: Optional[str] = None


class ApifyStatusResponse(BaseModel):
    """Live Apify account balance status."""

    configured: bool
    connected: bool
    username: str = ""
    plan: str = ""
    monthly_limit_usd: float = 0.0
    monthly_used_usd: float = 0.0
    remaining_usd: float = 0.0
    error: str = ""
