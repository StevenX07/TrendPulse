import { Disc3, Flame, Play, Pause, Rocket, Sparkles } from "lucide-react";
import type { WeeklySnapshot, WeeklySongTrend } from "../types/trends";
import { formatCompactNumber } from "../utils/format";

interface KpiHighlightsProps {
  snapshot: WeeklySnapshot;
  playingKey: string | null;
  isPlaying: boolean;
  onPlaySong: (song: WeeklySongTrend) => void;
  onSelectSong: (song: WeeklySongTrend) => void;
  onJumpTab: (tab: "most_streamed" | "fastest_growth" | "tiktok_viral" | "new_breakouts") => void;
}

export function KpiHighlights({
  snapshot,
  playingKey,
  isPlaying,
  onPlaySong,
  onSelectSong,
  onJumpTab,
}: KpiHighlightsProps) {
  const songMap = new Map(snapshot.songs.map((s) => [s.song_key, s]));
  const topStreamed = songMap.get(snapshot.summary.top_streamed_key) || snapshot.songs[0];
  const fastestGrowth = songMap.get(snapshot.summary.fastest_growth_key);
  const socialKey = snapshot.summary.top_social_key || snapshot.summary.top_tiktok_key || "";
  const topSocial = songMap.get(socialKey);

  const renderPlayMini = (song?: WeeklySongTrend) => {
    if (!song || (!song.preview_url && !song.youtube_video_id)) return null;
    const active = playingKey === song.song_key && isPlaying;
    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onPlaySong(song);
        }}
        title="Escuchar preview"
        className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-white/95 text-[#202124] shadow-sm transition hover:scale-105"
      >
        {active ? <Pause className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 translate-x-0.5 fill-current" />}
      </button>
    );
  };

  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {/* Card 1: #1 Más Streameada 7 Días */}
      <div
        onClick={() => topStreamed && onSelectSong(topStreamed)}
        className="md-card md-card-hover group cursor-pointer rounded-3xl bg-gradient-to-br from-[#E8F0FE] via-white to-white p-4"
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#D2E3FC] px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-[#174EA6]">
            <Disc3 className="h-3.5 w-3.5" />
            #1 Más Streameada 7D
          </span>
          {renderPlayMini(topStreamed)}
        </div>
        {topStreamed ? (
          <div className="flex items-center gap-3">
            {topStreamed.cover_url ? (
              <img
                src={topStreamed.cover_url}
                alt={topStreamed.title}
                className="h-12 w-12 shrink-0 rounded-2xl object-cover shadow-xs"
              />
            ) : null}
            <div className="min-w-0">
              <p className="truncate font-display text-base font-bold text-[#202124]">
                {topStreamed.title}
              </p>
              <p className="truncate text-xs font-medium text-[#5F6368]">{topStreamed.artist}</p>
              <p className="mt-1 text-xs font-bold text-[#1A73E8]">
                {topStreamed.spotify_weekly_streams
                  ? `${formatCompactNumber(topStreamed.spotify_weekly_streams)} streams 7D`
                  : topStreamed.youtube_weekly_views
                    ? `${formatCompactNumber(topStreamed.youtube_weekly_views)} views 7D`
                    : `Score ${topStreamed.trend_score}`}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-[#5F6368]">Sin datos aún</p>
        )}
      </div>

      {/* Card 2: Mayor Crecimiento Rápido */}
      <div
        onClick={() => (fastestGrowth ? onSelectSong(fastestGrowth) : onJumpTab("fastest_growth"))}
        className="md-card md-card-hover group cursor-pointer rounded-3xl bg-gradient-to-br from-[#E6F4EA] via-white to-white p-4"
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#CEEAD6] px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-[#0D652D]">
            <Rocket className="h-3.5 w-3.5" />
            Crecimiento Explosivo
          </span>
          {renderPlayMini(fastestGrowth)}
        </div>
        {fastestGrowth ? (
          <div className="flex items-center gap-3">
            {fastestGrowth.cover_url ? (
              <img
                src={fastestGrowth.cover_url}
                alt={fastestGrowth.title}
                className="h-12 w-12 shrink-0 rounded-2xl object-cover shadow-xs"
              />
            ) : null}
            <div className="min-w-0">
              <p className="truncate font-display text-base font-bold text-[#202124]">
                {fastestGrowth.title}
              </p>
              <p className="truncate text-xs font-medium text-[#5F6368]">{fastestGrowth.artist}</p>
              <p className="mt-1 text-xs font-bold text-[#137333]">
                {fastestGrowth.growth_badge || `Velocidad ${fastestGrowth.velocity_score}`}
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-[#5F6368]">Esperando datos</p>
        )}
      </div>

      {/* Card 3: Líder TikTok & Instagram Reels */}
      <div
        onClick={() => (topSocial ? onSelectSong(topSocial) : onJumpTab("tiktok_viral"))}
        className="md-card md-card-hover group cursor-pointer rounded-3xl bg-gradient-to-br from-[#FEF7E0] via-white to-white p-4"
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#FEEFC3] px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-[#B06000]">
            <Flame className="h-3.5 w-3.5" />
            Tendencia TikTok & Reels
          </span>
          {renderPlayMini(topSocial)}
        </div>
        {topSocial ? (
          <div className="flex items-center gap-3">
            {topSocial.cover_url ? (
              <img
                src={topSocial.cover_url}
                alt={topSocial.title}
                className="h-12 w-12 shrink-0 rounded-2xl object-cover shadow-xs"
              />
            ) : null}
            <div className="min-w-0">
              <p className="truncate font-display text-base font-bold text-[#202124]">
                {topSocial.title}
              </p>
              <p className="truncate text-xs font-medium text-[#5F6368]">{topSocial.artist}</p>
              <p className="mt-1 text-xs font-bold text-[#C56300]">
                {topSocial.tiktok_7d_growth_pct
                  ? `TikTok +${topSocial.tiktok_7d_growth_pct}% 7D`
                  : topSocial.reels_7d_growth_pct
                    ? `Reels +${topSocial.reels_7d_growth_pct}% 7D`
                    : topSocial.tiktok_explore_plays
                      ? `${formatCompactNumber(topSocial.tiktok_explore_plays)} plays Explore`
                      : `Top #${topSocial.tiktok_rank || topSocial.reels_rank || 1}`}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="font-display text-sm font-bold text-[#202124]">TikTok, Reels & Virales</p>
            <p className="text-xs leading-relaxed text-[#5F6368]">
              Los datos de TikTok multi-país, Instagram Reels, Shazam y Spotify Viral 50 se integran cada miércoles con <span className="font-semibold text-[#B06000]">fuentes de pago (Apify)</span>.
            </p>
          </div>
        )}
      </div>

      {/* Card 4: Cobertura + Recién llegadas */}
      <div
        onClick={() => onJumpTab("new_breakouts")}
        className="md-card md-card-hover cursor-pointer rounded-3xl bg-gradient-to-br from-[#FCE8E6] via-white to-white p-4"
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#FAD2CF] px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-[#A50E0E]">
            <Sparkles className="h-3.5 w-3.5" />
            Pulso Global Semanal
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2 pt-0.5">
          <div>
            <p className="font-display text-xl font-extrabold text-[#202124]">
              {snapshot.summary.total_songs}
            </p>
            <p className="text-[11px] font-medium text-[#5F6368]">Canciones</p>
          </div>
          <div>
            <p className="font-display text-xl font-extrabold text-[#1E8E3E]">
              {snapshot.summary.new_entries_count}
            </p>
            <p className="text-[11px] font-medium text-[#5F6368]">Nuevas (NEW)</p>
          </div>
          <div>
            <p className="font-display text-xl font-extrabold text-[#1A73E8]">
              {snapshot.summary.songs_with_preview}
            </p>
            <p className="text-[11px] font-medium text-[#5F6368]">Con Preview</p>
          </div>
        </div>
        <p className="mt-2 text-[11px] font-medium text-[#5F6368]">
          {snapshot.summary.multi_platform_count} canciones dominan 3+ plataformas simultáneamente
        </p>
      </div>
    </section>
  );
}
