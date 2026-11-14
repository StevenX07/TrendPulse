"""Local settings endpoints (token never exposed unmasked)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import Settings, mask_secret, write_env_updates
from ..deps import get_app_settings
from ..models import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_response(settings: Settings) -> SettingsResponse:
    return SettingsResponse(
        apify_configured=bool(settings.apify_api_token.strip()),
        apify_token_masked=mask_secret(settings.apify_api_token),
        apify_max_charge_per_run_usd=settings.apify_max_charge_per_run_usd,
        default_region=settings.default_region,
    )


@router.get("", response_model=SettingsResponse)
def read_settings(settings: Settings = Depends(get_app_settings)) -> SettingsResponse:
    """Return masked settings."""
    return _to_response(settings)


@router.put("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdateRequest) -> SettingsResponse:
    """Persist safe setting updates into local `.env`."""
    updates: dict[str, str] = {}
    if payload.apify_api_token is not None:
        updates["APIFY_API_TOKEN"] = payload.apify_api_token.strip()
    if payload.apify_max_charge_per_run_usd is not None:
        updates["APIFY_MAX_CHARGE_PER_RUN_USD"] = f"{payload.apify_max_charge_per_run_usd:.2f}"
    if payload.default_region is not None:
        updates["DEFAULT_REGION"] = payload.default_region.strip().upper() or "GLOBAL"

    updated = write_env_updates(updates) if updates else get_app_settings()
    return _to_response(updated)
