"""Unit and integration tests for cross-source merging, velocity scoring, WoW diff, and static export."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from collector.collect_trends import run_collection
from collector.models import WeeklySnapshot, WeeklySongTrend
from collector.scoring import assign_ranks_and_wow, merge_all_sources
from collector.sources_apify import ApifyCollectorClient


def test_merge_dedup_and_velocity_ranking() -> None:
    free_data = {
        "spotify_weekly": [
            {
                "rank": 1,
                "rank_change": "=",
                "title": "Steady Mega Hit",
                "artist": "Mega Star",
                "song_key": "mega-star__steady-mega-hit",
                "title_key": "steady-mega-hit",
                "weekly_streams": 30_000_000,
                "weekly_delta": -500_000,
                "weekly_growth_pct": -1.6,
                "weeks_on_chart": 40,
                "peak_rank": 1,
                "spotify_url": "https://open.spotify.com/track/1",
            },
            {
                "rank": 18,
                "rank_change": "+24",
                "title": "BbY WOW",
                "artist": "KAROL G",
                "song_key": "karol-g__bby-wow",
                "title_key": "bby-wow",
                "weekly_streams": 12_000_000,
                "weekly_delta": 6_000_000,
                "weekly_growth_pct": 100.0,
                "weeks_on_chart": 2,
                "peak_rank": 18,
                "spotify_url": "https://open.spotify.com/track/2",
            },
        ],
        "spotify_daily": [],
        "youtube_weekly": [],
        "ytmusic_charts": [],
        "apple_music": [
            {
                "rank": 4,
                "rank_change": "+10",
                "title": "BbY WOW",
                "artist": "KAROL G & Judeline",
                "song_key": "karol-g__bby-wow",
                "title_key": "bby-wow",
                "points": 12000,
                "points_delta": 900,
            }
        ],
        "itunes_rss": [],
        "deezer_chart": [],
        "billboard_hot100": [],
        "radio_shazam": [],
    }
    apify_data = {
        "history_songs": [
            {
                "song_key": "karol-g__bby-wow",
                "title_key": "bby-wow",
                "title": "BbY WOW",
                "artist": "KAROL G",
                "tiktok_rank": 2,
                "tiktok_chart_type": "viral",
                "tiktok_countries": ["US", "MX"],
                "tiktok_usage_count": 200_000,
                "tiktok_7d_usage_change": 95_000,
                "tiktok_7d_growth_pct": 90.5,
                "tiktok_is_viral": True,
            }
        ],
        "explore_songs": [],
        "reels_songs": [
            {
                "song_key": "karol-g__bby-wow",
                "title_key": "bby-wow",
                "title": "BbY WOW",
                "artist": "KAROL G",
                "reels_rank": 3,
                "reels_count": 120_000,
                "reels_7d_growth": 32_000,
                "reels_7d_growth_pct": 64.0,
            }
        ],
        "shazam_songs": [
            {
                "song_key": "karol-g__bby-wow",
                "title_key": "bby-wow",
                "title": "BbY WOW",
                "artist": "KAROL G",
                "shazam_global_rank": 11,
                "shazam_viral_rank": 4,
                "shazam_url": "https://www.shazam.com/song/bby",
            }
        ],
        "spotify_extra_songs": [
            {
                "song_key": "karol-g__bby-wow",
                "title_key": "bby-wow",
                "title": "BbY WOW",
                "artist": "KAROL G",
                "spotify_viral_rank": 6,
                "spotify_total_plays": 420_000_000,
                "release_date": "2026-11-01",
            }
        ],
    }

    merged = merge_all_sources(free_data, apify_data, updated_at="2026-11-14T05:00:00Z")
    assert len(merged) == 2

    by_key = {m["song_key"]: m for m in merged}
    rising = by_key["karol-g__bby-wow"]
    steady = by_key["mega-star__steady-mega-hit"]

    # All 5 platforms merged cleanly onto the single KAROL G entry
    assert set(rising["platforms"]) == {"Spotify", "Apple Music", "TikTok", "Reels", "Shazam"}
    assert rising["tiktok_countries"] == ["US", "MX"]
    assert rising["spotify_viral_rank"] == 6
    assert rising["shazam_viral_rank"] == 4
    assert rising["spotify_total_plays"] == 420_000_000
    assert rising["velocity_score"] > steady["velocity_score"]


def test_week_over_week_rank_delta() -> None:
    prev = WeeklySnapshot(
        week_id="2026-11-07",
        generated_at="2026-11-07T05:00:00Z",
        songs=[
            WeeklySongTrend(song_key="a__one", title="One", artist="A", trend_score=90.0, rank_overall=1),
            WeeklySongTrend(song_key="b__two", title="Two", artist="B", trend_score=70.0, rank_overall=5),
        ],
    )
    curr = [
        WeeklySongTrend(song_key="b__two", title="Two", artist="B", trend_score=92.0, velocity_score=80.0),
        WeeklySongTrend(song_key="a__one", title="One", artist="A", trend_score=88.0, velocity_score=20.0),
    ]
    ranked = assign_ranks_and_wow(curr, prev)
    assert ranked[0].song_key == "b__two"
    assert ranked[0].rank_overall == 1
    assert ranked[0].wow_rank_delta == 4  # climbed from #5 to #1
    assert ranked[1].wow_rank_delta == -1  # dropped from #1 to #2


def test_run_collection_writes_static_snapshots(tmp_path: Path) -> None:
    fake_free = {
        "spotify_weekly": [
            {
                "rank": 1,
                "rank_change": "NEW",
                "title": "Nueva Ola",
                "artist": "Feid",
                "song_key": "feid__nueva-ola",
                "title_key": "nueva-ola",
                "weekly_streams": 20_000_000,
                "weekly_delta": 5_000_000,
                "weekly_growth_pct": 33.3,
                "weeks_on_chart": 1,
                "peak_rank": 1,
                "spotify_url": "https://open.spotify.com/track/xyz",
            }
        ],
        "spotify_daily": [],
        "youtube_weekly": [],
        "ytmusic_charts": [],
        "apple_music": [],
        "itunes_rss": [],
        "deezer_chart": [],
        "billboard_hot100": [],
        "radio_shazam": [],
        "statuses": [
            {
                "id": "spotify_weekly",
                "name": "Spotify Global Weekly (Kworb)",
                "kind": "free",
                "status": "ok",
                "items_collected": 1,
                "cost_usd": 0.0,
                "note": "",
            }
        ],
    }

    with patch("collector.collect_trends.fetch_all_free_sources", new=AsyncMock(return_value=fake_free)):
        snap = asyncio.run(
            run_collection(
                mode="free",
                skip_enrichment=True,
                output_dir=tmp_path,
                cache_path=None,
            )
        )

    assert snap.schema_version == 3
    assert snap.summary.total_songs == 1
    assert snap.summary.total_cost_usd == 0.0
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "history.json").exists()
    assert (tmp_path / "archive" / f"{snap.week_id}.json").exists()


def test_run_collection_full_mode_with_5_apify_sources(tmp_path: Path) -> None:
    fake_free = {
        "spotify_weekly": [
            {
                "rank": 2,
                "rank_change": "+10",
                "title": "Viral Track",
                "artist": "Nova",
                "song_key": "nova__viral-track",
                "title_key": "viral-track",
                "weekly_streams": 18_000_000,
                "weekly_delta": 7_000_000,
                "weekly_growth_pct": 63.6,
                "weeks_on_chart": 2,
                "peak_rank": 2,
                "spotify_url": "https://open.spotify.com/track/viral123",
            }
        ],
        "spotify_daily": [],
        "youtube_weekly": [],
        "ytmusic_charts": [],
        "apple_music": [],
        "itunes_rss": [],
        "deezer_chart": [],
        "billboard_hot100": [],
        "radio_shazam": [],
        "statuses": [
            {
                "id": "spotify_weekly",
                "name": "Spotify Global Weekly (Kworb)",
                "kind": "free",
                "status": "ok",
                "items_collected": 1,
                "cost_usd": 0.0,
                "note": "",
            }
        ],
    }
    fake_apify = {
        "history_songs": [
            {
                "song_key": "nova__viral-track",
                "title_key": "viral-track",
                "title": "Viral Track",
                "artist": "Nova",
                "tiktok_rank": 1,
                "tiktok_countries": ["US", "MX"],
                "tiktok_7d_growth_pct": 85.0,
            }
        ],
        "explore_songs": [],
        "reels_songs": [
            {
                "song_key": "nova__viral-track",
                "title_key": "viral-track",
                "title": "Viral Track",
                "artist": "Nova",
                "reels_rank": 1,
                "reels_count": 90_000,
                "reels_7d_growth_pct": 55.0,
            }
        ],
        "shazam_songs": [
            {
                "song_key": "nova__viral-track",
                "title_key": "viral-track",
                "title": "Viral Track",
                "artist": "Nova",
                "shazam_global_rank": 4,
                "shazam_viral_rank": 2,
            }
        ],
        "spotify_extra_songs": [
            {
                "song_key": "nova__viral-track",
                "title_key": "viral-track",
                "title": "Viral Track",
                "artist": "Nova",
                "spotify_viral_rank": 1,
                "spotify_total_plays": 120_000_000,
                "release_date": "2026-11-05",
            }
        ],
        "statuses": [],
        "total_cost_usd": 0.91,
    }

    with (
        patch("collector.collect_trends.fetch_all_free_sources", new=AsyncMock(return_value=fake_free)),
        patch(
            "collector.collect_trends.ApifyCollectorClient.fetch_all_apify_trends",
            new=AsyncMock(return_value=fake_apify),
        ) as mock_apify,
    ):
        snap = asyncio.run(
            run_collection(
                mode="full",
                apify_token="apify_test",
                max_apify_usd=1.05,
                skip_enrichment=True,
                output_dir=tmp_path,
                cache_path=tmp_path / "cache.json",
            )
        )

    assert mock_apify.called
    assert snap.summary.reels_songs_count == 1
    assert snap.summary.shazam_viral_count == 1
    assert snap.summary.spotify_viral_count == 1
    assert snap.summary.top_social_key == "nova__viral-track"
    assert snap.summary.total_cost_usd == 0.91

    # Public static JSON files must omit exact dollar costs from repository output
    written_latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert "total_cost_usd" not in written_latest["summary"]
    assert all("cost_usd" not in src for src in written_latest["sources"])
    written_hist = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert all("total_cost_usd" not in wk for wk in written_hist["weeks"])


def test_run_collection_apify_crash_gracefully_falls_back_to_free(tmp_path: Path) -> None:
    fake_free = {
        "spotify_weekly": [
            {
                "rank": 1,
                "rank_change": "=",
                "title": "Solo Gratis",
                "artist": "Artista",
                "song_key": "artista__solo-gratis",
                "title_key": "solo-gratis",
                "weekly_streams": 22_000_000,
                "weekly_delta": 1_000_000,
                "weekly_growth_pct": 4.8,
                "weeks_on_chart": 3,
                "peak_rank": 1,
            }
        ],
        "spotify_daily": [],
        "youtube_weekly": [],
        "ytmusic_charts": [],
        "apple_music": [],
        "itunes_rss": [],
        "deezer_chart": [],
        "billboard_hot100": [],
        "radio_shazam": [],
        "statuses": [
            {
                "id": "spotify_weekly",
                "name": "Spotify Global Weekly (Kworb)",
                "kind": "free",
                "status": "ok",
                "items_collected": 1,
                "cost_usd": 0.0,
                "note": "",
            }
        ],
    }

    with (
        patch("collector.collect_trends.fetch_all_free_sources", new=AsyncMock(return_value=fake_free)),
        patch(
            "collector.collect_trends.ApifyCollectorClient.fetch_all_apify_trends",
            new=AsyncMock(side_effect=RuntimeError("Apify 503 down")),
        ),
    ):
        snap = asyncio.run(
            run_collection(
                mode="full",
                apify_token="apify_test",
                max_apify_usd=1.05,
                skip_enrichment=True,
                output_dir=tmp_path,
                cache_path=tmp_path / "cache.json",
            )
        )

    assert snap.summary.total_songs == 1
    assert snap.summary.free_sources_ok == 1
    assert snap.summary.apify_sources_ok == 0
    apify_statuses = [s for s in snap.sources if s.kind == "apify"]
    assert len(apify_statuses) == 5
    assert all(s.status == "error" and "Apify 503 down" in s.note for s in apify_statuses)
    assert (tmp_path / "latest.json").exists()


def test_apify_low_budget_runs_partial_sources_and_marks_remaining() -> None:
    client = ApifyCollectorClient(token="apify_test")

    async def fake_run_actor(actor_id: str, payload: dict, max_charge_usd: float, **kwargs):
        if "tiktok-trending-sounds-history" in actor_id:
            return (
                "r1",
                0.14,
                [
                    {
                        "record_type": "sound_insight",
                        "sound_id": "10",
                        "title": "DtMF",
                        "artist": "Bad Bunny",
                        "chart_type": "viral",
                        "rank": 1,
                        "usage_count": 100_000,
                        "usage_change": 20_000,
                        "usage_growth_pct": 25.0,
                        "is_original_sound": False,
                    }
                ],
            )
        return (
            "r2",
            0.09,
            [
                {
                    "chartType": "viral",
                    "rank": 1,
                    "trackTitle": "DtMF",
                    "artists": ["Bad Bunny"],
                    "songUrl": "https://www.shazam.com/song/1",
                }
            ],
        )

    with (
        patch.object(
            ApifyCollectorClient,
            "get_account_status",
            new=AsyncMock(return_value={"configured": True, "connected": True, "remaining_usd": 0.25}),
        ),
        patch.object(ApifyCollectorClient, "_run_actor", new=AsyncMock(side_effect=fake_run_actor)),
    ):
        res = asyncio.run(client.fetch_all_apify_trends(max_budget_usd=1.05))

    # $0.25 budget pays for tiktok_history ($0.14) + shazam ($0.09) = $0.23, leaving $0.02 -> rest skipped cleanly
    assert len(res["history_songs"]) == 1
    assert len(res["shazam_songs"]) == 1
    assert res["spotify_extra_songs"] == []
    assert res["reels_songs"] == []
    assert res["total_cost_usd"] == 0.23

    st_map = {s.id: s for s in res["statuses"]}
    assert st_map["tiktok_growth_history"].status == "ok"
    assert st_map["shazam_global_charts"].status == "ok"
    assert st_map["spotify_viral_plays"].status == "skipped"
    assert "insuficiente" in st_map["spotify_viral_plays"].note.lower()


def test_apify_invalid_token_returns_clear_error_statuses() -> None:
    client = ApifyCollectorClient(token="bad_token")
    with (
        patch.object(
            ApifyCollectorClient,
            "get_account_status",
            new=AsyncMock(
                return_value={
                    "configured": True,
                    "connected": False,
                    "auth_error": True,
                    "error": "Token de Apify inválido o revocado (HTTP 401).",
                }
            ),
        ),
        patch.object(ApifyCollectorClient, "_run_actor", new=AsyncMock()) as mock_run,
    ):
        res = asyncio.run(client.fetch_all_apify_trends(max_budget_usd=1.05))

    assert not mock_run.called
    assert len(res["statuses"]) == 5
    assert all(s.status == "error" and "401" in s.note for s in res["statuses"])
