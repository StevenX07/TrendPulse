"""FastAPI local API route tests for TrendPulse."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.deps import get_app_settings, get_public_data_dir
from backend.app.main import app
from collector.models import WeeklySnapshot


def _override_deps(tmp_path: Path, token: str = "") -> None:
    app.dependency_overrides[get_public_data_dir] = lambda: tmp_path
    app.dependency_overrides[get_app_settings] = lambda: Settings(
        apify_api_token=token,
        apify_max_charge_per_run_usd=1.05,
        default_region="GLOBAL",
    )


def test_health_snapshot_and_archive_routes(tmp_path: Path) -> None:
    _override_deps(tmp_path)
    try:
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        (tmp_path / "latest.json").write_text(
            json.dumps({"week_id": "2026-11-14", "songs": [], "summary": {"total_songs": 0}}),
            encoding="utf-8",
        )
        (archive_dir / "2026-11-14.json").write_text(
            json.dumps({"week_id": "2026-11-14", "songs": []}),
            encoding="utf-8",
        )

        client = TestClient(app)
        assert client.get("/api/health").json()["app"] == "TrendPulse"
        assert client.get("/api/snapshot").json()["week_id"] == "2026-11-14"
        assert client.get("/api/archive/2026-11-14").status_code == 200
        assert client.get("/api/archive/bad-date").status_code == 400
        assert client.get("/api/archive/2026-01-01").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_estimate_settings_masking_and_full_requires_token(tmp_path: Path) -> None:
    _override_deps(tmp_path, token="dummy_tok_1234567890abcdef")
    try:
        client = TestClient(app)
        s = client.get("/api/settings").json()
        assert s["apify_configured"] is True
        assert s["apify_token_masked"] == "dummy_...cdef"

        est_free = client.get("/api/apify/estimate?mode=free").json()
        assert est_free["estimated_usd"] == 0.0
        est_full = client.get("/api/apify/estimate?mode=full").json()
        assert est_full["estimated_usd"] >= 0.8
        assert len(est_full["breakdown"]) == 5
        assert est_full["monthly_4_weeks_usd"] <= 4.5

        # Missing token blocks mode=full with clean 400
        app.dependency_overrides[get_app_settings] = lambda: Settings(apify_api_token="")
        r_bad = client.post("/api/collect", json={"mode": "full"})
        assert r_bad.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_preview_history_apify_status_settings_put_and_collect_free(
    tmp_path: Path, monkeypatch
) -> None:
    _override_deps(tmp_path, token="dummy_tok_1234567890abcdef")
    try:
        (tmp_path / "history.json").write_text(
            json.dumps({
                "updated_at": "2026-11-14T00:00:00Z",
                "weeks": [{"week_id": "2026-11-14", "generated_at": "2026-11-14T00:00:00Z", "total_songs": 10, "top_song_title": "BbY WOW", "top_song_artist": "KAROL G"}],
            }),
            encoding="utf-8",
        )
        client = TestClient(app)

        hist = client.get("/api/history")
        assert hist.status_code == 200
        assert hist.json()["weeks"][0]["week_id"] == "2026-11-14"

        async def fake_resolve_live_preview(title: str, artist: str = "", deezer_url: str = "") -> dict:
            assert title == "BbY WOW"
            assert "deezer.com/track/123" in deezer_url
            return {"preview_url": "https://audio-ssl.itunes.apple.com/live.m4a", "preview_source": "itunes"}

        monkeypatch.setattr("backend.app.routers.trends.resolve_live_preview", fake_resolve_live_preview)
        prev = client.get(
            "/api/preview",
            params={"title": "BbY WOW", "artist": "KAROL G", "deezer_url": "https://www.deezer.com/track/123"},
        )
        assert prev.status_code == 200
        assert prev.json()["preview_source"] == "itunes"
        assert prev.json()["preview_url"].endswith("live.m4a")

        async def fake_status(self) -> dict:
            return {
                "configured": True,
                "connected": True,
                "username": "trendpulse_user",
                "plan": "FREE",
                "monthly_limit_usd": 5.0,
                "monthly_used_usd": 0.35,
                "remaining_usd": 4.65,
                "error": "",
            }

        monkeypatch.setattr("backend.app.routers.trends.ApifyCollectorClient.get_account_status", fake_status)
        st = client.get("/api/apify/status")
        assert st.status_code == 200
        assert st.json()["remaining_usd"] == 4.65

        captured_updates: dict = {}

        def fake_write_env(updates: dict[str, str]) -> Settings:
            captured_updates.update(updates)
            return Settings(
                apify_api_token=updates.get("APIFY_API_TOKEN", "dummy_tok_1234567890abcdef"),
                apify_max_charge_per_run_usd=float(updates.get("APIFY_MAX_CHARGE_PER_RUN_USD", "1.20")),
                default_region=updates.get("DEFAULT_REGION", "GLOBAL"),
            )

        monkeypatch.setattr("backend.app.routers.settings.write_env_updates", fake_write_env)
        put_res = client.put(
            "/api/settings",
            json={"apify_max_charge_per_run_usd": 1.2, "default_region": "CO"},
        )
        assert put_res.status_code == 200
        assert captured_updates["APIFY_MAX_CHARGE_PER_RUN_USD"] == "1.20"
        assert put_res.json()["default_region"] == "CO"

        async def fake_run_collection(mode: str, apify_token: str, max_apify_usd: float, output_dir: Path) -> WeeklySnapshot:
            assert mode == "free"
            assert output_dir == tmp_path
            return WeeklySnapshot(week_id="2026-11-14", generated_at="2026-11-14T00:00:00Z", mode=mode)

        monkeypatch.setattr("backend.app.routers.trends.run_collection", fake_run_collection)
        col = client.post("/api/collect", json={"mode": "free"})
        assert col.status_code == 200
        assert col.json()["mode"] == "free"
    finally:
        app.dependency_overrides.clear()
