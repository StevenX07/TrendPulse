import {
  ExternalLink,
  Loader2,
  Pause,
  Play,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  X,
  Youtube,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { WeeklySongTrend } from "../types/trends";
import { formatDuration } from "../utils/format";
import { isPreviewUrlExpired, resolveFreshPreview } from "../utils/previewResolver";

interface AudioPlayerPillProps {
  song: WeeklySongTrend | null;
  isPlaying: boolean;
  isLocalApi: boolean;
  onTogglePlay: () => void;
  onNext: () => void;
  onPrev: () => void;
  onClose: () => void;
  onSetPlaying: (playing: boolean) => void;
}

export function AudioPlayerPill({
  song,
  isPlaying,
  isLocalApi,
  onTogglePlay,
  onNext,
  onPrev,
  onClose,
  onSetPlaying,
}: AudioPlayerPillProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentKeyRef = useRef<string | null>(null);
  const recoveryTriedRef = useRef(false);
  const recoveryInFlightRef = useRef(false);

  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<string>("30s");
  const [isResolving, setIsResolving] = useState(false);
  const [fallbackToYoutube, setFallbackToYoutube] = useState(false);
  const [playError, setPlayError] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30);
  const [muted, setMuted] = useState(false);

  const recoverPreview = useCallback(
    async (targetSong: WeeklySongTrend) => {
      if (recoveryInFlightRef.current || recoveryTriedRef.current) {
        if (targetSong.youtube_video_id) {
          setActiveUrl(null);
          setFallbackToYoutube(true);
          setPlayError(false);
        } else {
          setPlayError(true);
          onSetPlaying(false);
        }
        return;
      }

      recoveryTriedRef.current = true;
      recoveryInFlightRef.current = true;
      setIsResolving(true);
      setPlayError(false);

      const resolved = await resolveFreshPreview(targetSong, isLocalApi);
      if (currentKeyRef.current !== targetSong.song_key) {
        return;
      }
      recoveryInFlightRef.current = false;
      setIsResolving(false);

      if (resolved?.url) {
        setActiveUrl(resolved.url);
        setActiveSource(resolved.source || "live");
        setFallbackToYoutube(false);
        setPlayError(false);
      } else if (targetSong.youtube_video_id) {
        setActiveUrl(null);
        setFallbackToYoutube(true);
        setPlayError(false);
      } else {
        setActiveUrl(null);
        setPlayError(true);
        onSetPlaying(false);
      }
    },
    [isLocalApi, onSetPlaying],
  );

  // Initialize or proactively refresh expired Deezer signed preview URLs on song change
  useEffect(() => {
    if (!song) {
      currentKeyRef.current = null;
      return;
    }
    currentKeyRef.current = song.song_key;
    recoveryTriedRef.current = false;
    recoveryInFlightRef.current = false;
    setCurrentTime(0);
    setDuration(30);
    setPlayError(false);

    if (song.preview_url && !isPreviewUrlExpired(song.preview_url)) {
      setActiveUrl(song.preview_url);
      setActiveSource(song.preview_source || "30s");
      setFallbackToYoutube(false);
      setIsResolving(false);
      return;
    }

    if (song.preview_url && isPreviewUrlExpired(song.preview_url)) {
      setActiveUrl(null);
      setFallbackToYoutube(false);
      void recoverPreview(song);
      return;
    }

    setActiveUrl(null);
    setIsResolving(false);
    setFallbackToYoutube(Boolean(song.youtube_video_id));
  }, [song, recoverPreview]);

  const hasDirectAudio = Boolean(activeUrl && !fallbackToYoutube);
  const hasYoutubeFallback = Boolean((fallbackToYoutube || !song?.preview_url) && song?.youtube_video_id && !hasDirectAudio);

  // Sync <audio> element with resolved preview URL and play state
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !song) return;

    if (!activeUrl || fallbackToYoutube) {
      audio.pause();
      if (audio.hasAttribute("src")) {
        audio.removeAttribute("src");
        audio.load();
      }
      setCurrentTime(0);
      return;
    }

    if (audio.src !== activeUrl) {
      audio.src = activeUrl;
      setCurrentTime(0);
      setDuration(30);
    }

    if (isPlaying) {
      audio.play().catch((err: unknown) => {
        if (currentKeyRef.current !== song.song_key) return;
        const name = err instanceof Error ? err.name : "";
        if (name === "AbortError") return;
        if (name === "NotAllowedError") {
          onSetPlaying(false);
          return;
        }
        void recoverPreview(song);
      });
    } else {
      audio.pause();
    }
  }, [song, activeUrl, fallbackToYoutube, isPlaying, onSetPlaying, recoverPreview]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.muted = muted;
    }
  }, [muted]);

  if (!song) return null;

  const pct = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  const externalFallbackUrl = song.spotify_url || song.deezer_url || song.apple_music_url || song.youtube_url;

  return (
    <div className="fixed bottom-3 left-1/2 z-40 w-[calc(100%-1rem)] max-w-2xl -translate-x-1/2 pb-[env(safe-area-inset-bottom)] sm:bottom-4 sm:w-[calc(100%-1.5rem)]">
      <audio
        ref={audioRef}
        preload="metadata"
        onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime || 0)}
        onLoadedMetadata={() => {
          if (audioRef.current && Number.isFinite(audioRef.current.duration)) {
            setDuration(audioRef.current.duration || 30);
          }
        }}
        onError={() => {
          if (song && currentKeyRef.current === song.song_key && activeUrl) {
            void recoverPreview(song);
          }
        }}
        onEnded={onNext}
      />

      {/* YouTube Mini Embed Popover when direct audio is missing or unavailable */}
      {hasYoutubeFallback && isPlaying && (
        <div className="md-pill-shadow mb-2 overflow-hidden rounded-3xl border border-[#DADCE0] bg-white p-2">
          <div className="mb-1.5 flex items-center justify-between px-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#C5221F]">
              <Youtube className="h-4 w-4" />
              Preview vía YouTube (respaldo directo sin audio 30s)
            </span>
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer rounded-full p-1 text-[#5F6368] hover:bg-[#F1F3F4]"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="aspect-video w-full overflow-hidden rounded-2xl bg-black">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube.com/embed/${song.youtube_video_id}?autoplay=1`}
              title={`${song.title} YouTube preview`}
              allow="autoplay; encrypted-media"
              allowFullScreen
            />
          </div>
        </div>
      )}

      {/* Floating Pill Bar */}
      <div className="md-pill-shadow rounded-3xl border border-[#DADCE0] bg-white/95 px-3 py-2.5 backdrop-blur-md sm:px-4 sm:py-3">
        <div className="flex items-center justify-between gap-3">
          {/* Artwork & Info */}
          <div className="flex min-w-0 flex-1 items-center gap-3">
            {song.cover_url ? (
              <img
                src={song.cover_url}
                alt={song.title}
                className="h-10 w-10 shrink-0 rounded-full border border-[#E8EAED] object-cover"
              />
            ) : null}
            <div className="min-w-0 flex-1">
              <p className="truncate font-display text-xs font-bold text-[#202124] sm:text-sm">
                {song.title}
              </p>
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-[#5F6368]">
                <span className="truncate">{song.artist}</span>
                <span>·</span>
                {isResolving ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-[#E8F0FE] px-2 py-0.5 text-[10px] font-semibold text-[#1967D2]">
                    <Loader2 className="h-2.5 w-2.5 animate-spin" />
                    Renovando audio...
                  </span>
                ) : playError ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-[#FCE8E6] px-2 py-0.5 text-[10px] font-semibold text-[#C5221F]">
                    Audio no disponible aquí
                    {externalFallbackUrl && (
                      <a
                        href={externalFallbackUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-0.5 underline"
                      >
                        Abrir
                        <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    )}
                  </span>
                ) : (
                  <span className="rounded-full bg-[#F1F3F4] px-2 py-0.5 text-[10px] font-semibold text-[#3C4043]">
                    {hasDirectAudio
                      ? `Preview ${activeSource}`
                      : "Preview YouTube"}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Transport Controls */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onPrev}
              aria-label="Canción anterior"
              className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[#5F6368] transition hover:bg-[#F1F3F4] hover:text-[#202124]"
            >
              <SkipBack className="h-4 w-4" />
            </button>

            <button
              type="button"
              onClick={() => {
                if (playError && song) {
                  recoveryTriedRef.current = false;
                  void recoverPreview(song);
                  onSetPlaying(true);
                  return;
                }
                onTogglePlay();
              }}
              aria-label={isPlaying ? "Pausar" : "Reproducir"}
              className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-full bg-[#1A73E8] text-white shadow-xs transition hover:bg-[#1765CC] active:scale-95"
            >
              {isResolving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isPlaying ? (
                <Pause className="h-4 w-4 fill-current" />
              ) : (
                <Play className="h-4 w-4 translate-x-0.5 fill-current" />
              )}
            </button>

            <button
              type="button"
              onClick={onNext}
              aria-label="Siguiente canción"
              className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[#5F6368] transition hover:bg-[#F1F3F4] hover:text-[#202124]"
            >
              <SkipForward className="h-4 w-4" />
            </button>

            {hasDirectAudio && (
              <button
                type="button"
                onClick={() => setMuted((m) => !m)}
                aria-label={muted ? "Activar sonido" : "Silenciar"}
                className="hidden h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[#5F6368] transition hover:bg-[#F1F3F4] sm:flex"
              >
                {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar reproductor"
              className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[#5F6368] transition hover:bg-[#F1F3F4] hover:text-[#202124]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Interactive Scrub Progress Bar (direct MP3/M4A previews) */}
        {hasDirectAudio && (
          <div className="mt-2 flex items-center gap-2.5 px-1">
            <span className="w-8 text-right text-[10px] font-medium tabular-nums text-[#5F6368]">
              {formatDuration(currentTime) || "0:00"}
            </span>
            <input
              type="range"
              min={0}
              max={duration || 30}
              step={0.1}
              value={currentTime}
              onChange={(e) => {
                const nextTime = Number(e.target.value);
                setCurrentTime(nextTime);
                if (audioRef.current) {
                  audioRef.current.currentTime = nextTime;
                }
              }}
              aria-label="Progreso de previsualización"
              className="h-1 flex-1 cursor-pointer accent-[#1A73E8]"
              style={{
                background: `linear-gradient(to right, #1A73E8 ${pct}%, #E8EAED ${pct}%)`,
              }}
            />
            <span className="w-8 text-right text-[10px] font-medium tabular-nums text-[#5F6368]">
              {formatDuration(duration) || "0:30"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
