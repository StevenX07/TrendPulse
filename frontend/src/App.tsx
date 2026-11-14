import { AlertTriangle, Loader2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  checkLocalApiAvailable,
  loadArchiveWeek,
  loadHistoryIndex,
  loadLatestSnapshot,
} from "./api/client";
import { AudioPlayerPill } from "./components/AudioPlayerPill";
import { KpiHighlights } from "./components/KpiHighlights";
import { SongDetailModal } from "./components/SongDetailModal";
import { SourcesGuideView } from "./components/SourcesGuideView";
import { TrendList } from "./components/TrendList";
import { TrendTabsBar } from "./components/TrendTabsBar";
import { TopAppBar } from "./components/TopAppBar";
import type {
  HistoryWeekEntry,
  PlatformFilter,
  TrendTab,
  WeeklySnapshot,
  WeeklySongTrend,
} from "./types/trends";
import { getProblemSources } from "./utils/sources";

const EMPTY_SNAPSHOT: WeeklySnapshot = {
  schema_version: 3,
  app_name: "TrendPulse",
  week_id: "",
  generated_at: "",
  mode: "free",
  region: "GLOBAL",
  summary: {
    total_songs: 0,
    songs_with_preview: 0,
    tiktok_songs_count: 0,
    reels_songs_count: 0,
    shazam_viral_count: 0,
    spotify_top50_count: 0,
    spotify_viral_count: 0,
    new_entries_count: 0,
    multi_platform_count: 0,
    free_sources_ok: 0,
    apify_sources_ok: 0,
    top_streamed_key: "",
    fastest_growth_key: "",
    top_social_key: "",
  },
  sources: [],
  songs: [],
};

export function App() {
  const [isLocalApi, setIsLocalApi] = useState(false);
  const [loading, setLoading] = useState(true);
  const [snapshot, setSnapshot] = useState<WeeklySnapshot>(EMPTY_SNAPSHOT);
  const [historyWeeks, setHistoryWeeks] = useState<HistoryWeekEntry[]>([]);
  const [selectedWeekId, setSelectedWeekId] = useState("");
  const [loadError, setLoadError] = useState("");

  // Navigation & Filters
  const [activeTab, setActiveTab] = useState<TrendTab>("most_streamed");
  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [onlyPlayable, setOnlyPlayable] = useState(false);
  const [onlyMultiPlatform, setOnlyMultiPlatform] = useState(false);

  // Audio Preview Player & Modals
  const [playingSong, setPlayingSong] = useState<WeeklySongTrend | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [detailSong, setDetailSong] = useState<WeeklySongTrend | null>(null);
  const [dismissedNoticeWeek, setDismissedNoticeWeek] = useState("");

  useEffect(() => {
    let mounted = true;
    async function boot() {
      setLoading(true);
      try {
        const localOk = await checkLocalApiAvailable();
        if (!mounted) return;
        setIsLocalApi(localOk);

        const [snap, hist] = await Promise.all([
          loadLatestSnapshot(localOk),
          loadHistoryIndex(localOk),
        ]);
        if (!mounted) return;
        setSnapshot(snap);
        setSelectedWeekId(snap.week_id);
        setHistoryWeeks(hist.weeks || []);
      } catch (err) {
        if (!mounted) return;
        setLoadError(err instanceof Error ? err.message : "No se pudo cargar el snapshot");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    boot();
    return () => {
      mounted = false;
    };
  }, []);

  const handleSelectWeek = async (weekId: string) => {
    setSelectedWeekId(weekId);
    setLoading(true);
    try {
      const snap =
        historyWeeks[0]?.week_id === weekId
          ? await loadLatestSnapshot(isLocalApi)
          : await loadArchiveWeek(weekId, isLocalApi);
      setSnapshot(snap);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Error cargando archivo semanal");
    } finally {
      setLoading(false);
    }
  };

  const problemSources = useMemo(() => getProblemSources(snapshot), [snapshot]);

  const filteredSongs = useMemo(() => {
    let list = [...snapshot.songs];

    // Tab filtering & sorting
    if (activeTab === "sources") {
      return [];
    } else if (activeTab === "fastest_growth") {
      list.sort((a, b) => b.velocity_score - a.velocity_score || b.trend_score - a.trend_score);
    } else if (activeTab === "tiktok_viral") {
      list = list
        .filter(
          (s) =>
            s.platforms.includes("TikTok") ||
            s.platforms.includes("Reels") ||
            s.tiktok_rank !== null ||
            Boolean(s.reels_rank),
        )
        .sort(
          (a, b) =>
            Math.max(b.tiktok_7d_growth_pct || 0, b.reels_7d_growth_pct || 0) -
              Math.max(a.tiktok_7d_growth_pct || 0, a.reels_7d_growth_pct || 0) ||
            b.velocity_score - a.velocity_score ||
            (b.tiktok_explore_plays || 0) - (a.tiktok_explore_plays || 0),
        );
    } else if (activeTab === "new_breakouts") {
      list = list
        .filter((s) => {
          const wks = s.spotify_weeks_on_chart ?? s.billboard_weeks ?? s.youtube_weeks_on_chart;
          return (
            s.is_new_entry ||
            (wks !== null && wks <= 3) ||
            (s.shazam_viral_rank !== null && s.shazam_viral_rank !== undefined && s.shazam_viral_rank <= 25) ||
            (s.shazam_rank !== null && s.shazam_rank <= 25)
          );
        })
        .sort((a, b) => b.velocity_score - a.velocity_score || b.trend_score - a.trend_score);
    } else if (activeTab === "platform_radar") {
      if (platformFilter === "spotify") {
        list = list
          .filter((s) => s.spotify_rank !== null)
          .sort((a, b) => (a.spotify_rank || 999) - (b.spotify_rank || 999));
      } else if (platformFilter === "spotify_top50") {
        list = list
          .filter((s) => Boolean(s.spotify_top50_rank))
          .sort((a, b) => (a.spotify_top50_rank || 999) - (b.spotify_top50_rank || 999));
      } else if (platformFilter === "spotify_viral") {
        list = list
          .filter((s) => Boolean(s.spotify_viral_rank))
          .sort((a, b) => (a.spotify_viral_rank || 999) - (b.spotify_viral_rank || 999));
      } else if (platformFilter === "youtube") {
        list = list
          .filter((s) => s.youtube_rank !== null)
          .sort((a, b) => (a.youtube_rank || 999) - (b.youtube_rank || 999));
      } else if (platformFilter === "reels") {
        list = list
          .filter((s) => s.platforms.includes("Reels") || Boolean(s.reels_rank))
          .sort(
            (a, b) =>
              (b.reels_7d_growth_pct || 0) - (a.reels_7d_growth_pct || 0) ||
              (a.reels_rank || 999) - (b.reels_rank || 999),
          );
      } else if (platformFilter === "apple") {
        list = list
          .filter((s) => s.apple_rank !== null)
          .sort((a, b) => (a.apple_rank || 999) - (b.apple_rank || 999));
      } else if (platformFilter === "billboard") {
        list = list
          .filter((s) => s.billboard_rank !== null)
          .sort((a, b) => (a.billboard_rank || 999) - (b.billboard_rank || 999));
      } else if (platformFilter === "shazam") {
        list = list
          .filter((s) => Boolean(s.shazam_global_rank || s.shazam_viral_rank || s.shazam_rank))
          .sort(
            (a, b) =>
              (a.shazam_viral_rank || a.shazam_global_rank || a.shazam_rank || 999) -
              (b.shazam_viral_rank || b.shazam_global_rank || b.shazam_rank || 999),
          );
      } else {
        list.sort(
          (a, b) => b.platform_count - a.platform_count || b.trend_score - a.trend_score,
        );
      }
    } else {
      // most_streamed
      list.sort(
        (a, b) =>
          b.trend_score - a.trend_score ||
          (b.spotify_weekly_streams || 0) - (a.spotify_weekly_streams || 0),
      );
    }

    // Search filter
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (s) =>
          s.title.toLowerCase().includes(q) ||
          s.artist.toLowerCase().includes(q) ||
          s.genres.some((g) => g.toLowerCase().includes(q)),
      );
    }

    if (onlyPlayable) {
      list = list.filter((s) => Boolean(s.preview_url || s.youtube_video_id));
    }
    if (onlyMultiPlatform) {
      list = list.filter((s) => s.platform_count >= 3);
    }

    return list;
  }, [
    snapshot.songs,
    activeTab,
    platformFilter,
    searchQuery,
    onlyPlayable,
    onlyMultiPlatform,
  ]);

  const playableQueue = useMemo(
    () => filteredSongs.filter((s) => Boolean(s.preview_url || s.youtube_video_id)),
    [filteredSongs],
  );

  const handlePlaySong = useCallback(
    (song: WeeklySongTrend) => {
      if (playingSong?.song_key === song.song_key) {
        setIsPlaying((prev) => !prev);
      } else {
        setPlayingSong(song);
        setIsPlaying(true);
      }
    },
    [playingSong],
  );

  const stepQueue = useCallback(
    (dir: 1 | -1) => {
      if (!playingSong || playableQueue.length === 0) return;
      const idx = playableQueue.findIndex((s) => s.song_key === playingSong.song_key);
      if (idx === -1) {
        setPlayingSong(playableQueue[0]);
        setIsPlaying(true);
        return;
      }
      const nextIdx = (idx + dir + playableQueue.length) % playableQueue.length;
      setPlayingSong(playableQueue[nextIdx]);
      setIsPlaying(true);
    },
    [playingSong, playableQueue],
  );

  return (
    <div className="min-h-screen bg-[#F8F9FA] pb-28 text-[#202124]">
      <TopAppBar
        snapshot={snapshot}
        historyWeeks={historyWeeks}
        selectedWeekId={selectedWeekId}
        onSelectWeek={handleSelectWeek}
        onOpenSourcesInfo={() => setActiveTab("sources")}
      />

      <main className="mx-auto max-w-7xl space-y-3.5 px-3.5 pt-3 sm:space-y-5 sm:px-6 sm:pt-5">
        {loadError && (
          <div className="rounded-2xl border border-[#FAD2CF] bg-[#FCE8E6] px-4 py-3 text-sm font-medium text-[#C5221F]">
            {loadError}
          </div>
        )}

        {problemSources.length > 0 &&
          activeTab !== "sources" &&
          dismissedNoticeWeek !== snapshot.generated_at && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-[#FDD663] bg-[#FEF7E0] px-4 py-3 text-xs text-[#202124]">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#B06000]" />
                <p className="leading-relaxed">
                  <strong>{problemSources.length} fuente(s) no se completaron</strong> en esta lectura (
                  {problemSources.map((s) => s.name).join(", ")}). Se conservó la actualización con las fuentes gratuitas y las que sí respondieron.
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab("sources")}
                  className="cursor-pointer rounded-full bg-[#B06000] px-3 py-1.5 font-display text-xs font-bold text-white transition hover:bg-[#8C4D00]"
                >
                  Ver detalle en Fuentes
                </button>
                <button
                  type="button"
                  aria-label="Ocultar aviso"
                  onClick={() => setDismissedNoticeWeek(snapshot.generated_at)}
                  className="cursor-pointer rounded-full p-1 text-[#5F6368] hover:bg-white/70"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}

        <KpiHighlights
          snapshot={snapshot}
          playingKey={playingSong?.song_key || null}
          isPlaying={isPlaying}
          onPlaySong={handlePlaySong}
          onSelectSong={setDetailSong}
          onJumpTab={(t) => setActiveTab(t)}
        />

        <TrendTabsBar
          activeTab={activeTab}
          onChangeTab={setActiveTab}
          platformFilter={platformFilter}
          onChangePlatformFilter={setPlatformFilter}
          searchQuery={searchQuery}
          onChangeSearch={setSearchQuery}
          onlyPlayable={onlyPlayable}
          onToggleOnlyPlayable={() => setOnlyPlayable((v) => !v)}
          onlyMultiPlatform={onlyMultiPlatform}
          onToggleOnlyMultiPlatform={() => setOnlyMultiPlatform((v) => !v)}
          resultCount={filteredSongs.length}
        />

        {loading ? (
          <div className="md-card flex items-center justify-center gap-3 rounded-3xl p-12 text-sm font-medium text-[#5F6368]">
            <Loader2 className="h-5 w-5 animate-spin text-[#1A73E8]" />
            <span>Cargando tendencias musicales...</span>
          </div>
        ) : activeTab === "sources" ? (
          <SourcesGuideView snapshot={snapshot} />
        ) : (
          <TrendList
            songs={filteredSongs}
            activeTab={activeTab}
            playingKey={playingSong?.song_key || null}
            isPlaying={isPlaying}
            onPlaySong={handlePlaySong}
            onSelectSong={setDetailSong}
          />
        )}
      </main>

      <AudioPlayerPill
        song={playingSong}
        isPlaying={isPlaying}
        isLocalApi={isLocalApi}
        onTogglePlay={() => setIsPlaying((p) => !p)}
        onNext={() => stepQueue(1)}
        onPrev={() => stepQueue(-1)}
        onClose={() => {
          setIsPlaying(false);
          setPlayingSong(null);
        }}
        onSetPlaying={setIsPlaying}
      />

      <SongDetailModal
        song={detailSong}
        playingKey={playingSong?.song_key || null}
        isPlaying={isPlaying}
        onPlaySong={handlePlaySong}
        onClose={() => setDetailSong(null)}
      />
    </div>
  );
}

export default App;
