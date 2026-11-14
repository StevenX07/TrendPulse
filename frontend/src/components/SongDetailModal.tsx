import { ExternalLink, Flame, Music2, Pause, Play, Radio, TrendingUp, X, Youtube } from "lucide-react";
import { useState } from "react";
import type { WeeklySongTrend } from "../types/trends";
import { formatCompactNumber, formatDuration, formatSignedCompact } from "../utils/format";

interface SongDetailModalProps {
  song: WeeklySongTrend | null;
  playingKey: string | null;
  isPlaying: boolean;
  onPlaySong: (song: WeeklySongTrend) => void;
  onClose: () => void;
}

export function SongDetailModal({
  song,
  playingKey,
  isPlaying,
  onPlaySong,
  onClose,
}: SongDetailModalProps) {
  const [showYtEmbed, setShowYtEmbed] = useState(false);
  if (!song) return null;

  const isCurrentPlaying = playingKey === song.song_key && isPlaying;
  const canPreviewAudio = Boolean(song.preview_url);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-[#202124]/45 p-0 backdrop-blur-xs sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90dvh] w-full max-w-2xl overflow-y-auto rounded-t-3xl bg-white p-4 shadow-2xl sm:rounded-3xl sm:p-6"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 sm:gap-4">
          <div className="flex min-w-0 items-center gap-3 sm:gap-4">
            {song.cover_url ? (
              <img
                src={song.cover_url}
                alt={song.title}
                className="h-16 w-16 shrink-0 rounded-2xl object-cover shadow-sm sm:h-20 sm:w-20"
              />
            ) : (
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-[#F1F3F4] text-[#80868B] sm:h-20 sm:w-20">
                <Music2 className="h-7 w-7 sm:h-8 sm:w-8" />
              </div>
            )}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-[#E8F0FE] px-2.5 py-0.5 font-display text-xs font-bold text-[#1967D2]">
                  #{song.rank_overall} Global 7D
                </span>
                <span className="rounded-full bg-[#E6F4EA] px-2.5 py-0.5 font-display text-xs font-bold text-[#137333]">
                  Velocidad #{song.rank_growth}
                </span>
                {song.is_new_entry && (
                  <span className="rounded-full bg-[#FCE8E6] px-2.5 py-0.5 text-xs font-extrabold text-[#C5221F]">
                    NEW
                  </span>
                )}
              </div>
              <h2 className="mt-1.5 font-display text-xl font-extrabold leading-tight text-[#202124]">
                {song.title}
              </h2>
              <p className="text-sm font-medium text-[#5F6368]">{song.artist}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[#5F6368]">
                {song.genres.map((g) => (
                  <span key={g} className="rounded-full bg-[#F1F3F4] px-2.5 py-0.5 font-medium">
                    {g}
                  </span>
                ))}
                {song.bpm ? (
                  <span className="rounded-full bg-[#F1F3F4] px-2.5 py-0.5 font-medium">
                    {Math.round(song.bpm)} BPM
                  </span>
                ) : null}
                {song.duration_sec ? (
                  <span className="rounded-full bg-[#F1F3F4] px-2.5 py-0.5 font-medium">
                    {formatDuration(song.duration_sec)}
                  </span>
                ) : null}
                {song.release_date ? (
                  <span className="rounded-full bg-[#F1F3F4] px-2.5 py-0.5 font-medium">
                    Lanz. {song.release_date}
                  </span>
                ) : null}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar detalle"
            className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-[#F1F3F4] text-[#5F6368] transition hover:bg-[#E8EAED] hover:text-[#202124]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Preview Action Bar */}
        <div className="mt-5 flex flex-wrap items-center gap-2.5">
          {(canPreviewAudio || song.youtube_video_id) && (
            <button
              type="button"
              onClick={() => onPlaySong(song)}
              className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-[#1A73E8] px-5 py-2.5 font-display text-xs font-bold text-white shadow-xs transition hover:bg-[#1765CC]"
            >
              {isCurrentPlaying ? (
                <>
                  <Pause className="h-4 w-4 fill-current" />
                  <span>Pausar preview</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>{canPreviewAudio ? "Escuchar preview 30s" : "Reproducir preview"}</span>
                </>
              )}
            </button>
          )}

          {song.youtube_video_id && (
            <button
              type="button"
              onClick={() => setShowYtEmbed((v) => !v)}
              className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-[#DADCE0] bg-white px-4 py-2 text-xs font-semibold text-[#3C4043] transition hover:bg-[#F1F3F4]"
            >
              <Youtube className="h-4 w-4 text-[#C5221F]" />
              <span>{showYtEmbed ? "Ocultar video" : "Ver video en modal"}</span>
            </button>
          )}
        </div>

        {showYtEmbed && song.youtube_video_id && (
          <div className="mt-4 aspect-video w-full overflow-hidden rounded-2xl bg-black">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube.com/embed/${song.youtube_video_id}?autoplay=1`}
              title={song.title}
              allow="autoplay; encrypted-media"
              allowFullScreen
            />
          </div>
        )}

        {/* Metrics Grid across Platforms */}
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {/* Spotify */}
          <div className="rounded-2xl border border-[#E8EAED] bg-[#F8F9FA] p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#137333]">
                Spotify Últimos 7 Días
              </span>
              {song.spotify_rank && (
                <span className="rounded-full bg-[#E6F4EA] px-2.5 py-0.5 text-xs font-bold text-[#137333]">
                  #{song.spotify_rank} ({song.spotify_rank_change || "="})
                </span>
              )}
            </div>
            <p className="mt-2 font-display text-2xl font-extrabold text-[#202124]">
              {song.spotify_weekly_streams ? formatCompactNumber(song.spotify_weekly_streams) : "No en Top 200"}
            </p>
            <p className="mt-0.5 text-xs text-[#5F6368]">
              {song.spotify_weekly_delta !== null
                ? `Cambio 7D: ${formatSignedCompact(song.spotify_weekly_delta)} (${
                    song.spotify_weekly_growth_pct !== null ? `${song.spotify_weekly_growth_pct > 0 ? "+" : ""}${song.spotify_weekly_growth_pct}%` : "—"
                  })`
                : song.spotify_daily_streams
                  ? `Hoy: ${formatCompactNumber(song.spotify_daily_streams)} streams`
                  : "Sin variación semanal registrada"}
            </p>
            {(song.spotify_weeks_on_chart || song.spotify_total_plays || song.spotify_top50_rank || song.spotify_viral_rank) && (
              <p className="mt-1 text-[11px] text-[#80868B]">
                {song.spotify_weeks_on_chart ? `${song.spotify_weeks_on_chart} sem. · Pico #${song.spotify_peak_rank || song.spotify_rank}` : ""}
                {song.spotify_top50_rank ? ` · Top 50 Global #${song.spotify_top50_rank}` : ""}
                {song.spotify_viral_rank ? ` · Viral Global #${song.spotify_viral_rank}` : ""}
                {song.spotify_total_plays ? ` · ${formatCompactNumber(song.spotify_total_plays)} plays acumulados` : ""}
              </p>
            )}
          </div>

          {/* YouTube */}
          <div className="rounded-2xl border border-[#E8EAED] bg-[#F8F9FA] p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#C5221F]">
                YouTube Últimos 7 Días
              </span>
              {song.youtube_rank && (
                <span className="rounded-full bg-[#FCE8E6] px-2.5 py-0.5 text-xs font-bold text-[#C5221F]">
                  #{song.youtube_rank} ({song.youtube_rank_change || "="})
                </span>
              )}
            </div>
            <p className="mt-2 font-display text-2xl font-extrabold text-[#202124]">
              {song.youtube_weekly_views ? formatCompactNumber(song.youtube_weekly_views) : "No en Top 200"}
            </p>
            <p className="mt-0.5 text-xs text-[#5F6368]">
              {song.youtube_weekly_delta !== null
                ? `Cambio 7D: ${formatSignedCompact(song.youtube_weekly_delta)} (${
                    song.youtube_weekly_growth_pct !== null ? `${song.youtube_weekly_growth_pct > 0 ? "+" : ""}${song.youtube_weekly_growth_pct}%` : "—"
                  })`
                : song.youtube_rank
                  ? "En chart global de YouTube Music"
                  : "Sin datos en Top 200 semanal"}
            </p>
          </div>

          {/* TikTok */}
          <div className="rounded-2xl border border-[#E8EAED] bg-[#F8F9FA] p-4">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[#B06000]">
                <Flame className="h-3.5 w-3.5" />
                TikTok Sonido / Viral
              </span>
              {song.tiktok_rank && (
                <span className="rounded-full bg-[#FEF7E0] px-2.5 py-0.5 text-xs font-bold text-[#B06000]">
                  #{song.tiktok_rank} {song.tiktok_chart_type}
                </span>
              )}
            </div>
            {song.tiktok_7d_growth_pct !== null || song.tiktok_explore_plays ? (
              <>
                <p className="mt-2 font-display text-2xl font-extrabold text-[#202124]">
                  {song.tiktok_7d_growth_pct !== null
                    ? `+${song.tiktok_7d_growth_pct}%`
                    : formatCompactNumber(song.tiktok_explore_plays)}
                </p>
                <p className="mt-0.5 text-xs text-[#5F6368]">
                  {song.tiktok_usage_count
                    ? `${formatCompactNumber(song.tiktok_usage_count)} usos totales (${formatSignedCompact(song.tiktok_7d_usage_change)} en 7D)`
                    : `${song.tiktok_explore_videos || 0} videos virales en muestra Explore`}
                </p>
                {song.tiktok_countries && song.tiktok_countries.length > 0 && (
                  <p className="mt-1 text-[11px] font-semibold text-[#B06000]">
                    Mercados: {song.tiktok_countries.join(" · ")}
                  </p>
                )}
              </>
            ) : song.reels_count || song.reels_7d_growth_pct ? (
              <>
                <p className="mt-2 font-display text-2xl font-extrabold text-[#B80672]">
                  {song.reels_7d_growth_pct !== null && song.reels_7d_growth_pct !== undefined
                    ? `+${song.reels_7d_growth_pct}%`
                    : formatCompactNumber(song.reels_count)}
                </p>
                <p className="mt-0.5 text-xs text-[#5F6368]">
                  Instagram Reels · {song.reels_count ? `${formatCompactNumber(song.reels_count)} reels` : ""}
                  {song.reels_7d_growth ? ` (${formatSignedCompact(song.reels_7d_growth)} en 7D)` : ""}
                </p>
              </>
            ) : (
              <p className="mt-2 text-sm text-[#5F6368]">No detectada en esta lectura de TikTok / Reels</p>
            )}
          </div>

          {/* Instagram Reels 7D card when both TikTok and Reels are present */}
          {(song.tiktok_7d_growth_pct !== null || song.tiktok_explore_plays) &&
            (song.reels_count || song.reels_7d_growth_pct) && (
              <div className="rounded-2xl border border-[#E8EAED] bg-[#FCE8F3]/40 p-4 sm:col-span-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#B80672]">
                    Instagram Reels Audio 7D
                  </span>
                  {song.reels_rank && (
                    <span className="rounded-full bg-[#FCE8F3] px-2.5 py-0.5 text-xs font-bold text-[#B80672]">
                      #{song.reels_rank} Crecimiento Reels
                    </span>
                  )}
                </div>
                <p className="mt-1.5 text-xs text-[#3C4043]">
                  <strong>{formatCompactNumber(song.reels_count)}</strong> Reels activos ·{" "}
                  {song.reels_7d_growth_pct ? `+${song.reels_7d_growth_pct}% en 7D` : ""}
                  {song.reels_7d_growth ? ` (${formatSignedCompact(song.reels_7d_growth)} reels en 7D)` : ""}
                </p>
              </div>
            )}

          {/* Apple / Billboard / Shazam */}
          <div className="rounded-2xl border border-[#E8EAED] bg-[#F8F9FA] p-4">
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[#1967D2]">
                <TrendingUp className="h-3.5 w-3.5" />
                Apple · Billboard · Shazam
              </span>
            </div>
            <div className="mt-2 space-y-1.5 text-xs text-[#3C4043]">
              <p>
                <strong>Apple Music Global:</strong>{" "}
                {song.apple_rank ? `#${song.apple_rank} (${song.apple_points || 0} pts)` : "—"}
              </p>
              <p>
                <strong>Billboard Hot 100:</strong>{" "}
                {song.billboard_rank
                  ? `#${song.billboard_rank} (antes ${song.billboard_last_week ? `#${song.billboard_last_week}` : "NEW"} · pico #${song.billboard_peak || song.billboard_rank})`
                  : "—"}
              </p>
              <p className="flex flex-wrap items-center gap-1">
                <Radio className="h-3.5 w-3.5 text-[#007B83]" />
                <strong>Shazam / Radio US:</strong>{" "}
                {song.shazam_global_rank || song.shazam_rank
                  ? `Top #${song.shazam_global_rank || song.shazam_rank}`
                  : "—"}
                {song.shazam_viral_rank ? ` · Viral #${song.shazam_viral_rank}` : ""}
                {song.radio_audience_m ? ` · Radio ${song.radio_audience_m}M` : ""}
              </p>
            </div>
          </div>
        </div>

        {/* TikTok & Instagram Reels Sample Videos */}
        {(song.tiktok_samples.length > 0 || (song.reels_samples && song.reels_samples.length > 0)) && (
          <div className="mt-5">
            <h3 className="font-display text-sm font-bold text-[#202124]">
              Videos virales recientes (TikTok y Reels)
            </h3>
            <div className="mt-2 space-y-2">
              {[
                ...song.tiktok_samples.map((v) => ({ ...v, tag: "TikTok" })),
                ...(song.reels_samples || []).map((v) => ({ ...v, tag: "Reels" })),
              ].map((vid, i) => (
                <a
                  key={`${vid.url}-${i}`}
                  href={vid.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between rounded-2xl border border-[#E8EAED] bg-[#F8F9FA] px-4 py-2.5 text-xs transition hover:border-[#DADCE0] hover:bg-[#F1F3F4]"
                >
                  <div className="min-w-0 pr-3">
                    <p className="truncate font-semibold text-[#202124]">
                      <span
                        className={`mr-1.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                          vid.tag === "Reels"
                            ? "bg-[#FCE8F3] text-[#B80672]"
                            : "bg-[#FEF7E0] text-[#B06000]"
                        }`}
                      >
                        {vid.tag}
                      </span>
                      {vid.creator ? `@${vid.creator}` : `Video viral ${vid.tag}`}
                    </p>
                    {vid.caption && <p className="truncate text-[#5F6368]">{vid.caption}</p>}
                  </div>
                  <div className="flex shrink-0 items-center gap-3 text-[#5F6368]">
                    {vid.plays > 0 && (
                      <span className="font-semibold text-[#202124]">
                        {formatCompactNumber(vid.plays)} plays
                      </span>
                    )}
                    <ExternalLink className="h-3.5 w-3.5" />
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* External Platform Links */}
        <div className="mt-6 flex flex-wrap gap-2 border-t border-[#E8EAED] pt-4">
          {song.spotify_url && (
            <a
              href={song.spotify_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#E6F4EA] px-4 py-2 text-xs font-bold text-[#137333] transition hover:brightness-95"
            >
              <span>Abrir en Spotify</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {song.youtube_url && (
            <a
              href={song.youtube_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#FCE8E6] px-4 py-2 text-xs font-bold text-[#C5221F] transition hover:brightness-95"
            >
              <span>Ver en YouTube</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {song.tiktok_sound_url && (
            <a
              href={song.tiktok_sound_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#FEF7E0] px-4 py-2 text-xs font-bold text-[#B06000] transition hover:brightness-95"
            >
              <span>Sonido en TikTok</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {song.reels_audio_url && (
            <a
              href={song.reels_audio_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#FCE8F3] px-4 py-2 text-xs font-bold text-[#B80672] transition hover:brightness-95"
            >
              <span>Audio en Reels</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {song.shazam_url && (
            <a
              href={song.shazam_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#E4F7FB] px-4 py-2 text-xs font-bold text-[#007B83] transition hover:brightness-95"
            >
              <span>Shazam</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {song.apple_music_url && (
            <a
              href={song.apple_music_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#F3E8FD] px-4 py-2 text-xs font-bold text-[#7B1FA2] transition hover:brightness-95"
            >
              <span>Apple Music</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {song.deezer_url && (
            <a
              href={song.deezer_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#F1F3F4] px-4 py-2 text-xs font-bold text-[#3C4043] transition hover:bg-[#E8EAED]"
            >
              <span>Deezer</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
