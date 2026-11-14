import { ArrowUpRight, Disc3, Pause, Play, Radio, Video } from "lucide-react";
import type { TrendTab, WeeklySongTrend } from "../types/trends";
import { formatCompactNumber, formatDuration, formatSignedCompact } from "../utils/format";

interface TrendListProps {
  songs: WeeklySongTrend[];
  activeTab: TrendTab;
  playingKey: string | null;
  isPlaying: boolean;
  onPlaySong: (song: WeeklySongTrend) => void;
  onSelectSong: (song: WeeklySongTrend) => void;
}

const PLATFORM_STYLES: Record<string, string> = {
  Spotify: "bg-[#E6F4EA] text-[#137333]",
  YouTube: "bg-[#FCE8E6] text-[#C5221F]",
  TikTok: "bg-[#FEF7E0] text-[#B06000]",
  Reels: "bg-[#FCE8F3] text-[#B80672]",
  "Apple Music": "bg-[#F3E8FD] text-[#7B1FA2]",
  Billboard: "bg-[#E8F0FE] text-[#1967D2]",
  Deezer: "bg-[#F1F3F4] text-[#3C4043]",
  Shazam: "bg-[#E4F7FB] text-[#007B83]",
};

function getPlatformRankLabel(song: WeeklySongTrend, platform: string): string {
  switch (platform) {
    case "Spotify": {
      const parts: string[] = [];
      if (song.spotify_rank) parts.push(`Spotify #${song.spotify_rank}`);
      if (song.spotify_top50_rank) parts.push(`Top 50 #${song.spotify_top50_rank}`);
      if (song.spotify_viral_rank) parts.push(`Viral #${song.spotify_viral_rank}`);
      return parts.length > 0 ? parts.join(" · ") : "Spotify";
    }
    case "YouTube":
      return song.youtube_rank ? `YT #${song.youtube_rank}` : "YouTube";
    case "TikTok":
      if (song.tiktok_7d_growth_pct) return `TikTok +${song.tiktok_7d_growth_pct.toFixed(0)}%`;
      return song.tiktok_rank ? `TikTok #${song.tiktok_rank}` : "TikTok";
    case "Reels":
      if (song.reels_7d_growth_pct) return `Reels +${song.reels_7d_growth_pct.toFixed(0)}%`;
      return song.reels_rank ? `Reels #${song.reels_rank}` : "Reels";
    case "Apple Music":
      return song.apple_rank ? `Apple #${song.apple_rank}` : "Apple Music";
    case "Billboard":
      return song.billboard_rank ? `Billboard #${song.billboard_rank}` : "Billboard";
    case "Shazam":
      if (song.shazam_viral_rank) return `Shazam Viral #${song.shazam_viral_rank}`;
      if (song.shazam_global_rank) return `Shazam #${song.shazam_global_rank}`;
      return song.shazam_rank ? `Shazam #${song.shazam_rank}` : "Shazam";
    default:
      return platform;
  }
}

export function TrendList({
  songs,
  activeTab,
  playingKey,
  isPlaying,
  onPlaySong,
  onSelectSong,
}: TrendListProps) {
  if (songs.length === 0) {
    return (
      <div className="md-card rounded-3xl p-10 text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#F1F3F4] text-[#5F6368]">
          <Disc3 className="h-6 w-6" />
        </div>
        <h3 className="font-display text-lg font-bold text-[#202124]">
          {activeTab === "tiktok_viral"
            ? "Aún no hay datos de TikTok o Reels en esta lectura"
            : "No se encontraron canciones con estos filtros"}
        </h3>
        <p className="mx-auto mt-1 max-w-md text-sm text-[#5F6368]">
          {activeTab === "tiktok_viral"
            ? "Las fuentes gratuitas están activas. Los datos de TikTok multi-país, Instagram Reels, Shazam y Spotify Viral 50 se actualizan automáticamente cada miércoles a las 00:00 (UTC-5) mediante fuentes de pago."
            : "Prueba limpiando el buscador o desactivando los filtros de plataforma."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {songs.map((song, idx) => {
        const displayRank = idx + 1;
        const canAudio = Boolean(song.preview_url);
        const canYoutube = Boolean(song.youtube_video_id);
        const canPreview = canAudio || canYoutube;
        const isCurrent = playingKey === song.song_key;
        const isCurrentPlaying = isCurrent && isPlaying;

        const scoreValue =
          activeTab === "fastest_growth" || activeTab === "new_breakouts"
            ? song.velocity_score
            : song.trend_score;

        const primaryScoreLabel =
          activeTab === "fastest_growth" || activeTab === "new_breakouts"
            ? "Crecimiento"
            : "Pulso 7D";

        return (
          <article
            key={song.song_key}
            onClick={() => onSelectSong(song)}
            className={`md-card md-card-hover flex cursor-pointer flex-col gap-3 rounded-3xl p-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-3.5 ${
              isCurrent ? "border-[#1A73E8] ring-2 ring-[#E8F0FE]" : ""
            }`}
          >
            {/* Left Section: Rank + Cover/Play + Title/Artist/Chips */}
            <div className="flex min-w-0 flex-1 items-center gap-3.5">
              {/* Rank & WoW Change */}
              <div className="flex w-9 shrink-0 flex-col items-center text-center">
                <span
                  className={`font-display text-lg font-extrabold leading-none ${
                    displayRank <= 3 ? "text-[#1A73E8]" : "text-[#3C4043]"
                  }`}
                >
                  {displayRank}
                </span>
                {song.wow_rank_delta !== null && song.wow_rank_delta !== 0 ? (
                  <span
                    className={`mt-1 text-[10px] font-bold ${
                      song.wow_rank_delta > 0 ? "text-[#1E8E3E]" : "text-[#D93025]"
                    }`}
                  >
                    {song.wow_rank_delta > 0 ? `↑${song.wow_rank_delta}` : `↓${Math.abs(song.wow_rank_delta)}`}
                  </span>
                ) : song.is_new_entry ? (
                  <span className="mt-1 rounded-full bg-[#FCE8E6] px-1.5 py-0.5 text-[9px] font-extrabold text-[#C5221F]">
                    NEW
                  </span>
                ) : null}
              </div>

              {/* Cover + Instant Play Overlay */}
              <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-2xl bg-[#F1F3F4]">
                {song.cover_url ? (
                  <img
                    src={song.cover_url}
                    alt={`${song.title} portada`}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-[#80868B]">
                    <Disc3 className="h-6 w-6" />
                  </div>
                )}

                {canPreview && (
                  <button
                    type="button"
                    aria-label={isCurrentPlaying ? `Pausar ${song.title}` : `Previsualizar ${song.title}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onPlaySong(song);
                    }}
                    className={`absolute inset-0 flex cursor-pointer items-center justify-center transition ${
                      isCurrentPlaying
                        ? "bg-[#202124]/55 text-white opacity-100"
                        : "bg-[#202124]/45 text-white opacity-90 sm:opacity-0 sm:hover:opacity-100"
                    }`}
                  >
                    {isCurrentPlaying ? (
                      <div className="flex items-end gap-0.5 h-4">
                        <span className="eq-bar-1 w-1 rounded-full bg-white h-full" />
                        <span className="eq-bar-2 w-1 rounded-full bg-white h-full" />
                        <span className="eq-bar-3 w-1 rounded-full bg-white h-full" />
                      </div>
                    ) : canAudio ? (
                      <Play className="h-5 w-5 translate-x-0.5 fill-current" />
                    ) : (
                      <Video className="h-5 w-5" />
                    )}
                  </button>
                )}
              </div>

              {/* Track Info & Badges */}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate font-display text-sm font-bold text-[#202124] sm:text-base">
                    {song.title}
                  </h3>
                  {song.growth_badge && song.growth_badge !== "Tendencia estable" && (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-[#E6F4EA] px-2 py-0.5 text-[11px] font-bold text-[#137333]">
                      <ArrowUpRight className="h-3 w-3" />
                      {song.growth_badge}
                    </span>
                  )}
                  {isCurrentPlaying && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-[#E8F0FE] px-2 py-0.5 text-[10px] font-bold text-[#1967D2]">
                      Sonando
                    </span>
                  )}
                </div>

                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[#5F6368]">
                  <span className="font-medium text-[#3C4043]">{song.artist}</span>
                  {song.genres[0] && (
                    <>
                      <span>·</span>
                      <span>{song.genres[0]}</span>
                    </>
                  )}
                  {song.bpm ? (
                    <>
                      <span>·</span>
                      <span>{Math.round(song.bpm)} BPM</span>
                    </>
                  ) : null}
                  {song.duration_sec ? (
                    <>
                      <span>·</span>
                      <span>{formatDuration(song.duration_sec)}</span>
                    </>
                  ) : null}
                </div>

                {/* Cross-Platform Pills */}
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  {song.platforms.slice(0, 6).map((plat) => (
                    <span
                      key={plat}
                      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        PLATFORM_STYLES[plat] || "bg-[#F1F3F4] text-[#5F6368]"
                      }`}
                    >
                      {getPlatformRankLabel(song, plat)}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Section: 7-Day Concrete Volumes + Score + Quick Play Button */}
            <div className="flex items-center justify-between gap-4 border-t border-[#F1F3F4] pt-2.5 sm:justify-end sm:border-t-0 sm:pt-0">
              {/* Key 7D Numbers */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-left sm:text-right">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-[#80868B]">
                    Spotify 7D
                  </p>
                  <p className="font-display text-xs font-bold text-[#202124] sm:text-sm">
                    {song.spotify_weekly_streams ? formatCompactNumber(song.spotify_weekly_streams) : "—"}
                  </p>
                  {song.spotify_weekly_delta ? (
                    <p
                      className={`text-[10px] font-semibold ${
                        song.spotify_weekly_delta > 0 ? "text-[#1E8E3E]" : "text-[#80868B]"
                      }`}
                    >
                      {formatSignedCompact(song.spotify_weekly_delta)}
                      {song.spotify_weekly_growth_pct !== null ? ` (${song.spotify_weekly_growth_pct > 0 ? "+" : ""}${song.spotify_weekly_growth_pct}%)` : ""}
                    </p>
                  ) : null}
                </div>

                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-[#80868B]">
                    {song.tiktok_usage_count || song.tiktok_explore_plays || song.reels_count
                      ? "TikTok / Reels / YT"
                      : "YouTube 7D"}
                  </p>
                  <p className="font-display text-xs font-bold text-[#202124] sm:text-sm">
                    {song.youtube_weekly_views
                      ? formatCompactNumber(song.youtube_weekly_views)
                      : song.tiktok_explore_plays
                        ? formatCompactNumber(song.tiktok_explore_plays)
                        : song.reels_count
                          ? `${formatCompactNumber(song.reels_count)} reels`
                          : "—"}
                  </p>
                  {song.tiktok_7d_growth_pct ? (
                    <p className="text-[10px] font-semibold text-[#B06000]">
                      TT +{song.tiktok_7d_growth_pct}% 7D
                    </p>
                  ) : song.reels_7d_growth_pct ? (
                    <p className="text-[10px] font-semibold text-[#B80672]">
                      Reels +{song.reels_7d_growth_pct}% 7D
                    </p>
                  ) : song.shazam_viral_rank ? (
                    <p className="text-[10px] font-semibold text-[#007B83]">
                      Shazam Viral #{song.shazam_viral_rank}
                    </p>
                  ) : song.shazam_global_rank || song.shazam_rank ? (
                    <p className="text-[10px] font-semibold text-[#007B83]">
                      Shazam #{song.shazam_global_rank || song.shazam_rank}
                    </p>
                  ) : null}
                </div>
              </div>

              {/* Score Pill */}
              <div className="flex flex-col items-end">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[#80868B]">
                  {primaryScoreLabel}
                </span>
                <div
                  className={`mt-0.5 rounded-full px-3 py-1 font-display text-sm font-extrabold ${
                    activeTab === "fastest_growth" || activeTab === "new_breakouts"
                      ? "bg-[#E6F4EA] text-[#137333]"
                      : activeTab === "tiktok_viral"
                        ? "bg-[#FEF7E0] text-[#B06000]"
                        : "bg-[#E8F0FE] text-[#1967D2]"
                  }`}
                >
                  {scoreValue.toFixed(0)}
                </div>
              </div>

              {/* Explicit Play Pill on Desktop */}
              {canPreview && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onPlaySong(song);
                  }}
                  title={canAudio ? "Escuchar preview de 30s" : "Reproducir video preview en YouTube"}
                  className={`hidden h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full border transition sm:flex ${
                    isCurrentPlaying
                      ? "border-[#1A73E8] bg-[#1A73E8] text-white"
                      : "border-[#DADCE0] bg-white text-[#3C4043] hover:border-[#1A73E8] hover:bg-[#E8F0FE] hover:text-[#1A73E8]"
                  }`}
                >
                  {isCurrentPlaying ? (
                    <Pause className="h-4 w-4 fill-current" />
                  ) : canAudio ? (
                    <Play className="h-4 w-4 translate-x-0.5 fill-current" />
                  ) : (
                    <Radio className="h-4 w-4" />
                  )}
                </button>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
