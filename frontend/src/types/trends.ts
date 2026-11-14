export type TrendTab =
  | "most_streamed"
  | "fastest_growth"
  | "tiktok_viral"
  | "new_breakouts"
  | "platform_radar"
  | "sources";

export type PlatformFilter =
  | "all"
  | "spotify"
  | "spotify_viral"
  | "youtube"
  | "reels"
  | "shazam"
  | "apple"
  | "billboard";

export interface SocialSampleVideo {
  url: string;
  creator: string;
  caption: string;
  plays: number;
  likes: number;
  published_at: string;
}

export type TikTokSampleVideo = SocialSampleVideo;

export interface SourceStatus {
  id: string;
  name: string;
  kind: "free" | "apify";
  status: "ok" | "skipped" | "error";
  items_collected: number;
  cost_usd?: number;
  note: string;
}

export interface WeeklySongTrend {
  song_key: string;
  title: string;
  artist: string;
  cover_url: string;
  preview_url: string;
  preview_source: string;
  duration_sec: number | null;
  bpm: number | null;
  release_date?: string;
  genres: string[];

  trend_score: number;
  velocity_score: number;
  rank_overall: number;
  rank_growth: number;
  wow_rank_delta: number | null;
  wow_score_delta: number | null;

  spotify_rank: number | null;
  spotify_rank_change: string | null;
  spotify_weekly_streams: number | null;
  spotify_weekly_delta: number | null;
  spotify_weekly_growth_pct: number | null;
  spotify_daily_streams: number | null;
  spotify_weeks_on_chart: number | null;
  spotify_peak_rank: number | null;
  spotify_viral_rank?: number | null;
  spotify_total_plays?: number | null;
  spotify_url: string;

  youtube_rank: number | null;
  youtube_rank_change: string | null;
  youtube_weekly_views: number | null;
  youtube_weekly_delta: number | null;
  youtube_weekly_growth_pct: number | null;
  youtube_weeks_on_chart: number | null;
  youtube_video_id: string;
  youtube_url: string;

  tiktok_rank: number | null;
  tiktok_chart_type: string;
  tiktok_countries?: string[];
  tiktok_usage_count: number | null;
  tiktok_7d_usage_change: number | null;
  tiktok_7d_growth_pct: number | null;
  tiktok_rank_change: number | null;
  tiktok_explore_videos: number | null;
  tiktok_explore_plays: number | null;
  tiktok_is_new: boolean;
  tiktok_is_viral: boolean;
  tiktok_is_commercial: boolean | null;
  tiktok_newest_age_days: number | null;
  tiktok_sound_id: string;
  tiktok_sound_url: string;
  tiktok_samples: SocialSampleVideo[];

  reels_rank?: number | null;
  reels_count?: number | null;
  reels_1d_growth?: number | null;
  reels_7d_growth?: number | null;
  reels_7d_growth_pct?: number | null;
  reels_audio_url?: string;
  reels_samples?: SocialSampleVideo[];

  apple_rank: number | null;
  apple_rank_change: string | null;
  apple_points: number | null;
  apple_points_delta: number | null;
  apple_music_url: string;

  billboard_rank: number | null;
  billboard_last_week: number | null;
  billboard_peak: number | null;
  billboard_weeks: number | null;

  deezer_rank: number | null;
  deezer_url: string;

  radio_rank: number | null;
  radio_audience_m: number | null;
  radio_audience_delta: number | null;
  shazam_rank: number | null;
  shazam_global_rank?: number | null;
  shazam_viral_rank?: number | null;
  shazam_url?: string;

  platforms: string[];
  platform_count: number;
  is_new_entry: boolean;
  growth_badge: string;
  updated_at: string;
}

export interface SnapshotSummary {
  total_songs: number;
  songs_with_preview: number;
  tiktok_songs_count: number;
  reels_songs_count?: number;
  shazam_viral_count?: number;
  spotify_viral_count?: number;
  new_entries_count: number;
  multi_platform_count: number;
  free_sources_ok: number;
  apify_sources_ok: number;
  total_cost_usd?: number;
  top_streamed_key: string;
  fastest_growth_key: string;
  top_social_key?: string;
  top_tiktok_key?: string;
}

export interface WeeklySnapshot {
  schema_version: number;
  app_name: string;
  week_id: string;
  generated_at: string;
  mode: "free" | "full";
  region: string;
  summary: SnapshotSummary;
  sources: SourceStatus[];
  songs: WeeklySongTrend[];
}

export interface HistoryWeekEntry {
  week_id: string;
  generated_at: string;
  mode: "free" | "full";
  total_songs: number;
  tiktok_songs_count: number;
  reels_songs_count?: number;
  total_cost_usd?: number;
  top_streamed_title: string;
  top_streamed_artist: string;
  fastest_growth_title: string;
  fastest_growth_artist: string;
  archive_path: string;
}

export interface HistoryIndex {
  updated_at: string;
  weeks: HistoryWeekEntry[];
}
