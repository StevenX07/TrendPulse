"""Pydantic schemas for TrendPulse weekly snapshots, multi-source song metrics, and history."""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SocialSampleVideo(BaseModel):
    """Sample TikTok or Instagram Reel clip using a trending song/sound."""

    url: str = ""
    creator: str = ""
    caption: str = ""
    plays: int = 0
    likes: int = 0
    published_at: str = ""


class SourceStatus(BaseModel):
    """Telemetry for a single free or Apify data source in a collection run."""

    id: str
    name: str
    kind: Literal["free", "apify"]
    status: Literal["ok", "skipped", "error"]
    items_collected: int = 0
    cost_usd: float = 0.0
    note: str = ""


class WeeklySongTrend(BaseModel):
    """Unified multi-platform song trend entry for 7-day volume, rapid growth, and previews."""

    song_key: str
    title: str
    artist: str
    cover_url: str = ""
    preview_url: str = ""
    preview_source: str = ""  # deezer | itunes | spotify | tiktok | ""
    duration_sec: Optional[int] = None
    bpm: Optional[float] = None
    release_date: str = ""
    genres: List[str] = Field(default_factory=list)

    # Computed Scores (0..100)
    trend_score: float = 0.0  # 7-day streaming volume & multi-platform dominance
    velocity_score: float = 0.0  # Rapid 7-day acceleration & breakout momentum

    # Computed Ranks inside Snapshot
    rank_overall: int = 0
    rank_growth: int = 0
    wow_rank_delta: Optional[int] = None  # Positive = climbed vs previous week
    wow_score_delta: Optional[float] = None

    # Spotify (Kworb Weekly/Daily + Apify Viral 50 & Play Counts)
    spotify_rank: Optional[int] = None
    spotify_rank_change: Optional[str] = None
    spotify_weekly_streams: Optional[int] = None
    spotify_weekly_delta: Optional[int] = None
    spotify_weekly_growth_pct: Optional[float] = None
    spotify_daily_streams: Optional[int] = None
    spotify_weeks_on_chart: Optional[int] = None
    spotify_peak_rank: Optional[int] = None
    spotify_viral_rank: Optional[int] = None
    spotify_total_plays: Optional[int] = None
    spotify_url: str = ""

    # YouTube (Kworb Weekly + YouTube Music Charts)
    youtube_rank: Optional[int] = None
    youtube_rank_change: Optional[str] = None
    youtube_weekly_views: Optional[int] = None
    youtube_weekly_delta: Optional[int] = None
    youtube_weekly_growth_pct: Optional[float] = None
    youtube_weeks_on_chart: Optional[int] = None
    youtube_video_id: str = ""
    youtube_url: str = ""

    # TikTok (Apify 7D History + Multi-Country Explore)
    tiktok_rank: Optional[int] = None
    tiktok_chart_type: str = ""
    tiktok_countries: List[str] = Field(default_factory=list)
    tiktok_usage_count: Optional[int] = None
    tiktok_7d_usage_change: Optional[int] = None
    tiktok_7d_growth_pct: Optional[float] = None
    tiktok_rank_change: Optional[int] = None
    tiktok_explore_videos: Optional[int] = None
    tiktok_explore_plays: Optional[int] = None
    tiktok_is_new: bool = False
    tiktok_is_viral: bool = False
    tiktok_is_commercial: Optional[bool] = None
    tiktok_newest_age_days: Optional[int] = None
    tiktok_sound_id: str = ""
    tiktok_sound_url: str = ""
    tiktok_samples: List[SocialSampleVideo] = Field(default_factory=list)

    # Instagram Reels (Apify Instagram Audio Tracker)
    reels_rank: Optional[int] = None
    reels_count: Optional[int] = None
    reels_1d_growth: Optional[int] = None
    reels_7d_growth: Optional[int] = None
    reels_7d_growth_pct: Optional[float] = None
    reels_audio_url: str = ""
    reels_samples: List[SocialSampleVideo] = Field(default_factory=list)

    # Shazam (Kworb Radio/Shazam + Apify Global Top 200 & Global Viral 50)
    shazam_rank: Optional[int] = None
    shazam_global_rank: Optional[int] = None
    shazam_viral_rank: Optional[int] = None
    shazam_url: str = ""

    # Apple Music & iTunes
    apple_rank: Optional[int] = None
    apple_rank_change: Optional[str] = None
    apple_points: Optional[int] = None
    apple_points_delta: Optional[int] = None
    apple_music_url: str = ""

    # Billboard Hot 100
    billboard_rank: Optional[int] = None
    billboard_last_week: Optional[int] = None
    billboard_peak: Optional[int] = None
    billboard_weeks: Optional[int] = None

    # Deezer
    deezer_rank: Optional[int] = None
    deezer_url: str = ""

    # US Radio (Kworb)
    radio_rank: Optional[int] = None
    radio_audience_m: Optional[float] = None
    radio_audience_delta: Optional[float] = None

    # Metadata & Badges
    platforms: List[str] = Field(default_factory=list)
    platform_count: int = 0
    is_new_entry: bool = False
    growth_badge: str = ""
    updated_at: str = ""


class SnapshotSummary(BaseModel):
    """High-level KPI highlights for a weekly snapshot."""

    total_songs: int = 0
    songs_with_preview: int = 0
    tiktok_songs_count: int = 0
    reels_songs_count: int = 0
    shazam_viral_count: int = 0
    spotify_viral_count: int = 0
    new_entries_count: int = 0
    multi_platform_count: int = 0
    free_sources_ok: int = 0
    apify_sources_ok: int = 0
    total_cost_usd: float = 0.0
    top_streamed_key: str = ""
    fastest_growth_key: str = ""
    top_social_key: str = ""


class WeeklySnapshot(BaseModel):
    """Complete JSON payload written to `frontend/public/data/latest.json`."""

    schema_version: int = 3
    app_name: str = "TrendPulse"
    week_id: str
    generated_at: str
    mode: Literal["free", "full"] = "free"
    region: str = "GLOBAL"
    summary: SnapshotSummary = Field(default_factory=SnapshotSummary)
    sources: List[SourceStatus] = Field(default_factory=list)
    songs: List[WeeklySongTrend] = Field(default_factory=list)


class HistoryWeekEntry(BaseModel):
    """Lightweight week entry stored in `frontend/public/data/history.json`."""

    week_id: str
    generated_at: str
    mode: Literal["free", "full"]
    total_songs: int
    tiktok_songs_count: int
    reels_songs_count: int = 0
    total_cost_usd: float = 0.0
    top_streamed_title: str = ""
    top_streamed_artist: str = ""
    fastest_growth_title: str = ""
    fastest_growth_artist: str = ""
    archive_path: str


class HistoryIndex(BaseModel):
    """Manifest of archived weekly snapshots for weekly selector."""

    updated_at: str
    weeks: List[HistoryWeekEntry] = Field(default_factory=list)
