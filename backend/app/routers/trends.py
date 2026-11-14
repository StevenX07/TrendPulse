"""Snapshot, weekly archive, live collection, and Apify status/cost endpoints."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from collector.collect_trends import run_collection
from collector.models import HistoryIndex, WeeklySnapshot
from collector.sources_apify import ApifyCollectorClient, estimate_apify_weekly_cost
from collector.sources_free import resolve_live_preview

from ..config import Settings
from ..deps import get_app_settings, get_public_data_dir
from ..models import ApifyStatusResponse, CollectRequest

router = APIRouter(prefix="/api", tags=["trends"])

_collection_lock = asyncio.Lock()


@router.get("/snapshot")
def get_latest_snapshot(data_dir: Path = Depends(get_public_data_dir)) -> Dict[str, Any]:
    """Return latest generated weekly snapshot JSON."""
    latest_path = data_dir / "latest.json"
    if not latest_path.exists():
        return WeeklySnapshot(week_id="", generated_at="").model_dump()
    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Snapshot corrupto: {exc}") from exc


@router.get("/history")
def get_history_index(data_dir: Path = Depends(get_public_data_dir)) -> Dict[str, Any]:
    """Return available weekly archive index."""
    hist_path = data_dir / "history.json"
    if not hist_path.exists():
        return HistoryIndex(updated_at="").model_dump()
    try:
        return json.loads(hist_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Historial corrupto: {exc}") from exc


@router.get("/archive/{week_id}")
def get_archived_snapshot(week_id: str, data_dir: Path = Depends(get_public_data_dir)) -> Dict[str, Any]:
    """Return an archived weekly snapshot (`YYYY-MM-DD`)."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", week_id):
        raise HTTPException(status_code=400, detail="Formato de semana inválido (usa YYYY-MM-DD).")
    target = data_dir / "archive" / f"{week_id}.json"
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"No existe snapshot para {week_id}.")
    return json.loads(target.read_text(encoding="utf-8"))


@router.get("/apify/status", response_model=ApifyStatusResponse)
async def apify_account_status(settings: Settings = Depends(get_app_settings)) -> ApifyStatusResponse:
    """Inspect remaining Apify free/paid credit ($0.00 API call)."""
    client = ApifyCollectorClient(token=settings.apify_api_token)
    data = await client.get_account_status()
    return ApifyStatusResponse.model_validate(data)


@router.get("/apify/estimate")
def apify_weekly_estimate(mode: str = "full") -> Dict[str, Any]:
    """Return transparent USD estimate for free vs full weekly run."""
    if mode == "free":
        return {
            "mode": "free",
            "estimated_usd": 0.0,
            "monthly_4_weeks_usd": 0.0,
            "formula": "$0.00 · 9 fuentes globales gratuitas (Spotify Weekly/Daily, YouTube Weekly, ytmusicapi, Apple Music, iTunes RSS, Deezer, Billboard Hot 100, Radio & Shazam)",
        }
    est = estimate_apify_weekly_cost()
    return {"mode": "full", **est}


@router.get("/preview")
async def get_fresh_preview(
    title: str,
    artist: str = "",
    deezer_url: str = "",
) -> Dict[str, str]:
    """Resolve a fresh non-expired 30s preview URL on demand ($0.00 iTunes/Deezer lookup)."""
    return await resolve_live_preview(title=title, artist=artist, deezer_url=deezer_url)


@router.post("/collect")
async def trigger_collection(
    req: CollectRequest,
    settings: Settings = Depends(get_app_settings),
    data_dir: Path = Depends(get_public_data_dir),
) -> Dict[str, Any]:
    """Run TrendPulse collector locally and save static JSON files."""
    if _collection_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Ya hay una actualización en curso. Espera unos segundos a que termine.",
        )

    if req.mode == "full" and not settings.apify_api_token.strip():
        raise HTTPException(
            status_code=400,
            detail="Falta configurar APIFY_API_TOKEN en Ajustes para ejecutar el paquete completo de 5 actores Apify.",
        )

    budget = req.max_apify_usd or settings.apify_max_charge_per_run_usd
    async with _collection_lock:
        snapshot = await run_collection(
            mode=req.mode,
            apify_token=settings.apify_api_token,
            max_apify_usd=budget,
            output_dir=data_dir,
        )
    return snapshot.model_dump()
