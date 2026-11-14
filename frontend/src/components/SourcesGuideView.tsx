import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  CreditCard,
  Database,
  Flame,
  Globe,
  Headphones,
  Rocket,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type { SourceStatus, WeeklySnapshot } from "../types/trends";
import { getProblemSources, isSourceIssue } from "../utils/sources";

interface SourcesGuideViewProps {
  snapshot: WeeklySnapshot;
}

interface SourceDocEntry {
  id: string;
  title: string;
  provider: string;
  cadence: string;
  extracts: string;
  accentBg: string;
  accentText: string;
}

const FREE_SOURCE_DOCS: SourceDocEntry[] = [
  {
    id: "spotify_weekly",
    title: "Spotify Global Weekly Top 200",
    provider: "Kworb.net · Spotify Charts",
    cadence: "Semanal (7D)",
    extracts:
      "Rankings Top 200 globales, streams exactos de los últimos 7 días, cambio neto, crecimiento %, semanas en lista y debuts (NEW).",
    accentBg: "bg-[#E6F4EA]",
    accentText: "text-[#137333]",
  },
  {
    id: "spotify_daily",
    title: "Spotify Global Daily Top 200",
    provider: "Kworb.net · Spotify Daily",
    cadence: "Diario",
    extracts:
      "Streams de las últimas 24 horas y debuts recién lanzados antes de que aparezcan en el corte semanal oficial.",
    accentBg: "bg-[#E6F4EA]",
    accentText: "text-[#137333]",
  },
  {
    id: "youtube_weekly",
    title: "YouTube Global Weekly Top 200",
    provider: "Kworb.net · YouTube Charts",
    cadence: "Semanal (7D)",
    extracts:
      "Vistas globales de videos musicales en 7 días, variación porcentual semanal, posición e IDs oficiales para video preview.",
    accentBg: "bg-[#FCE8E6]",
    accentText: "text-[#C5221F]",
  },
  {
    id: "ytmusic_charts",
    title: "YouTube Music Global Charts",
    provider: "ytmusicapi (sin API key)",
    cadence: "Tiempo real / Semanal",
    extracts:
      "Top canciones y videos en tendencia global en YouTube Music, portadas de alta resolución y enlaces directos.",
    accentBg: "bg-[#FCE8E6]",
    accentText: "text-[#C5221F]",
  },
  {
    id: "apple_music",
    title: "Apple Music Global Top 200",
    provider: "Kworb.net · Apple Worldwide",
    cadence: "Diario / Semanal",
    extracts:
      "Ranking mundial consolidado de Apple Music, puntuación ponderada multi-país y saltos diarios de posición.",
    accentBg: "bg-[#F3E8FD]",
    accentText: "text-[#7B1FA2]",
  },
  {
    id: "deezer_chart",
    title: "Deezer Global Chart & Previews",
    provider: "API Pública de Deezer",
    cadence: "Tiempo real",
    extracts:
      "Top 100 global de Deezer, duración, portadas HD y previews oficiales de audio MP3 de 30 segundos listos para reproducir.",
    accentBg: "bg-[#F1F3F4]",
    accentText: "text-[#3C4043]",
  },
  {
    id: "itunes_rss",
    title: "iTunes Top Songs RSS (US / GB / MX / ES / BR / DE)",
    provider: "Apple iTunes Public Feed",
    cadence: "Tiempo real",
    extracts:
      "Tendencias de compra directa en 6 mercados clave, género principal y previews AAC de 30s permanentes.",
    accentBg: "bg-[#F3E8FD]",
    accentText: "text-[#7B1FA2]",
  },
  {
    id: "billboard_hot100",
    title: "Billboard Hot 100 Weekly",
    provider: "Dataset abierto Hot 100",
    cadence: "Semanal",
    extracts:
      "Posición actual, semana previa, pico histórico (Peak) y semanas totales en la lista de referencia en EE. UU.",
    accentBg: "bg-[#E8F0FE]",
    accentText: "text-[#1967D2]",
  },
  {
    id: "radio_shazam",
    title: "Radio US & Shazam Cross-Rank",
    provider: "Kworb Radio / Shazam",
    cadence: "Diario",
    extracts:
      "Audiencia radial en millones (M), delta diario en radio y posición inicial en Shazam como radar de descubrimiento.",
    accentBg: "bg-[#E4F7FB]",
    accentText: "text-[#007B83]",
  },
];

const APIFY_SOURCE_DOCS: SourceDocEntry[] = [
  {
    id: "tiktok_growth_history",
    title: "TikTok 7D Crecimiento Multi-País",
    provider: "Apify · trendingtiktoksongs/tiktok-trending-sounds-history",
    cadence: "Semanal (top 100 sonidos)",
    extracts:
      "Tasa real de crecimiento en 7 días (%), usos totales, variación neta semanal en US, MX, BR y DE, además de ejemplos de videos.",
    accentBg: "bg-[#FEF7E0]",
    accentText: "text-[#B06000]",
  },
  {
    id: "tiktok_explore_sounds",
    title: "TikTok Explore 4 Mercados (US/GB/MX/ES)",
    provider: "Apify · s_actors/tiktok-trending-sounds-scraper",
    cadence: "Semanal (muestra 800 videos)",
    extracts:
      "Detección temprana de sonidos virales por región, reproducciones promedio, creadores destacados y bandera de sonido comercial.",
    accentBg: "bg-[#FEF7E0]",
    accentText: "text-[#B06000]",
  },
  {
    id: "instagram_reels_audio",
    title: "Instagram Reels Audio 7D",
    provider: "Apify · trendingtiktoksongs/instagram-audio-history",
    cadence: "Semanal (top 60 audios)",
    extracts:
      "Audios musicales con mayor aceleración en 1 y 7 días dentro de Instagram Reels, volumen de Reels activos y enlaces de ejemplo.",
    accentBg: "bg-[#FCE8F3]",
    accentText: "text-[#B80672]",
  },
  {
    id: "shazam_global_charts",
    title: "Shazam Top 200 & Viral 50 Global",
    provider: "Apify · automation-lab/shazam-charts-scraper",
    cadence: "Semanal (250 canciones)",
    extracts:
      "Clasificación oficial de las canciones más buscadas en el mundo (Top 200) y las que explotan más rápido (Viral 50 Global).",
    accentBg: "bg-[#E4F7FB]",
    accentText: "text-[#007B83]",
  },
  {
    id: "spotify_viral_plays",
    title: "Spotify Top 50 Global + Viral 50 + Reproducciones",
    provider: "Apify · eduair94/spotify-scraper",
    cadence: "Semanal (Top 50 oficial + Viral 50 + Top en alza)",
    extracts:
      "Playlist oficial Top 50: Global (37i9dQZEVXbMDoHDwVN2tF), ranking Spotify Viral 50 Global, reproducciones acumuladas históricas (`playCount`) y metadatos oficiales.",
    accentBg: "bg-[#E6F4EA]",
    accentText: "text-[#137333]",
  },
];

function StatusPill({
  live,
  snapshotMode,
}: {
  live?: SourceStatus;
  snapshotMode: "free" | "full";
}) {
  if (!live) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-[#F1F3F4] px-2.5 py-0.5 text-[11px] font-semibold text-[#5F6368]">
        <Clock className="h-3 w-3" />
        En espera
      </span>
    );
  }
  if (live.status === "error") {
    return (
      <span
        title={live.note}
        className="inline-flex items-center gap-1 rounded-full bg-[#FCE8E6] px-2.5 py-0.5 text-[11px] font-bold text-[#C5221F]"
      >
        <AlertTriangle className="h-3 w-3" />
        Fallo de ejecución
      </span>
    );
  }
  if (live.status === "skipped") {
    const issue = isSourceIssue(live, snapshotMode);
    if (issue) {
      return (
        <span
          title={live.note}
          className="inline-flex items-center gap-1 rounded-full bg-[#FEF7E0] px-2.5 py-0.5 text-[11px] font-bold text-[#B06000]"
        >
          <AlertTriangle className="h-3 w-3" />
          No disponible
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-[#F1F3F4] px-2.5 py-0.5 text-[11px] font-semibold text-[#5F6368]">
        <Clock className="h-3 w-3" />
        Solo lectura gratuita
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[#E6F4EA] px-2.5 py-0.5 text-[11px] font-bold text-[#137333]">
      <CheckCircle2 className="h-3 w-3" />
      {live.items_collected} registros
    </span>
  );
}

function SourceDocCard({
  doc,
  badgeLabel,
  live,
  snapshotMode,
}: {
  doc: SourceDocEntry;
  badgeLabel: string;
  live?: SourceStatus;
  snapshotMode: "free" | "full";
}) {
  const showIssueNote = Boolean(live && isSourceIssue(live, snapshotMode) && live.note);

  return (
    <article
      className={`md-card flex flex-col justify-between rounded-3xl p-4 ${
        live?.status === "error"
          ? "border-[#FAD2CF]"
          : showIssueNote
            ? "border-[#FDD663]"
            : ""
      }`}
    >
      <div>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <span
            className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${doc.accentBg} ${doc.accentText}`}
          >
            {badgeLabel}
          </span>
          <StatusPill live={live} snapshotMode={snapshotMode} />
        </div>
        <h4 className="mt-2.5 font-display text-sm font-bold text-[#202124]">
          {doc.title}
        </h4>
        <p className="mt-0.5 text-[11px] font-medium text-[#80868B]">{doc.provider}</p>
        <p className="mt-2 text-xs leading-relaxed text-[#5F6368]">{doc.extracts}</p>
        {showIssueNote && live && (
          <p
            className={`mt-2.5 rounded-2xl px-3 py-2 text-[11px] font-medium leading-snug ${
              live.status === "error"
                ? "bg-[#FCE8E6] text-[#C5221F]"
                : "bg-[#FEF7E0] text-[#B06000]"
            }`}
          >
            {live.note}
          </p>
        )}
      </div>
    </article>
  );
}

export function SourcesGuideView({
  snapshot,
}: SourcesGuideViewProps) {
  const statusMap = new Map(snapshot.sources.map((s) => [s.id, s]));
  const problemSources = getProblemSources(snapshot);

  return (
    <div className="space-y-6">
      {/* Incidences / Partial Degradation Alert if any source failed or was unavailable */}
      {problemSources.length > 0 && (
        <section className="md-card rounded-3xl border-[#FDD663] bg-[#FEF7E0]/75 p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#E37400] text-white">
              <AlertTriangle className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1 space-y-2">
              <div>
                <h3 className="font-display text-sm font-extrabold text-[#202124]">
                  {problemSources.length} fuente(s) no se completaron en esta lectura
                </h3>
                <p className="mt-0.5 text-xs leading-relaxed text-[#5F6368]">
                  La aplicación conservó la actualización semanal con las{" "}
                  <strong>{snapshot.summary.free_sources_ok} fuentes gratuitas</strong>{" "}
                  y las{" "}
                  <strong>{snapshot.summary.apify_sources_ok} fuentes de pago</strong>{" "}
                  que sí respondieron correctamente.
                </p>
              </div>
              <ul className="space-y-1.5">
                {problemSources.map((st) => (
                  <li
                    key={st.id}
                    className="flex flex-wrap items-baseline justify-between gap-2 rounded-2xl bg-white/90 px-3 py-2 text-xs"
                  >
                    <span className="font-bold text-[#202124]">{st.name}</span>
                    <span
                      className={`font-medium ${
                        st.status === "error" ? "text-[#C5221F]" : "text-[#B06000]"
                      }`}
                    >
                      {st.note || "No disponible temporalmente"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}
      {/* Top Overview Banner */}
      <section className="md-card rounded-3xl bg-gradient-to-br from-[#E8F0FE] via-white to-[#F8F9FA] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#D2E3FC] px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-[#174EA6]">
              <Database className="h-3.5 w-3.5" />
              Arquitectura de Datos · 14 Fuentes
            </span>
            <h2 className="font-display text-2xl font-extrabold tracking-tight text-[#202124]">
              ¿De dónde saca TrendPulse sus tendencias y métricas?
            </h2>
            <p className="text-sm leading-relaxed text-[#5F6368]">
              Cada miércoles a las <strong className="text-[#202124]">00:00 (hora local UTC-5)</strong>, TrendPulse combina{" "}
              <strong className="text-[#137333]">9 fuentes globales gratuitas</strong> con{" "}
              <strong className="text-[#B06000]">5 fuentes de pago mediante Apify</strong>{" "}
              para medir consumo real de 7 días, velocidad de crecimiento, señales sociales en TikTok/Reels y descubrimiento en Shazam y Spotify Viral 50.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-2xl border border-[#DADCE0] bg-white px-4 py-3 text-center">
              <p className="font-display text-xl font-extrabold text-[#1E8E3E]">
                {snapshot.summary.free_sources_ok}/9
              </p>
              <p className="text-[11px] font-semibold text-[#5F6368]">Gratuitas activas</p>
            </div>
            <div className="rounded-2xl border border-[#DADCE0] bg-white px-4 py-3 text-center">
              <p className="font-display text-xl font-extrabold text-[#E37400]">
                {snapshot.summary.apify_sources_ok}/5
              </p>
              <p className="text-[11px] font-semibold text-[#5F6368]">De pago (Apify)</p>
            </div>
          </div>
        </div>
      </section>

      {/* Scoring Logic Explained */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="md-card rounded-3xl p-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-[#E8F0FE] text-[#1A73E8]">
              <TrendingUp className="h-5 w-5" />
            </span>
            <div>
              <h3 className="font-display text-base font-bold text-[#202124]">
                Cómo se calcula «Pulso 7D» (0–100)
              </h3>
              <p className="text-xs text-[#5F6368]">Dominio real de streams y alcance multi-plataforma</p>
            </div>
          </div>
          <ul className="mt-3 space-y-2 text-xs leading-relaxed text-[#3C4043]">
            <li>
              • <strong className="text-[#137333]">Spotify 7D + Viral 50:</strong> hasta 39 pts basados en streams semanales globales y posición Top 200 / Viral 50.
            </li>
            <li>
              • <strong className="text-[#C5221F]">YouTube 7D Global:</strong> hasta 24 pts ponderando visualizaciones semanales y ranking mundial.
            </li>
            <li>
              • <strong className="text-[#1967D2]">Apple Music · Billboard · Deezer · Shazam:</strong> suman puntos adicionales por presencia simultánea en charts oficiales y búsquedas en Shazam.
            </li>
            <li>
              • <strong className="text-[#B06000]">TikTok & Instagram Reels + Presencia Cruzada:</strong> bonificación adicional por sonidos trending en videos cortos y por dominar 3 o más plataformas a la vez.
            </li>
          </ul>
        </div>

        <div className="md-card rounded-3xl p-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-[#E6F4EA] text-[#1E8E3E]">
              <Rocket className="h-5 w-5" />
            </span>
            <div>
              <h3 className="font-display text-base font-bold text-[#202124]">
                Cómo se calcula «Crecimiento Rápido» (0–100)
              </h3>
              <p className="text-xs text-[#5F6368]">Velocidad de despegue en los últimos 7 días</p>
            </div>
          </div>
          <ul className="mt-3 space-y-2 text-xs leading-relaxed text-[#3C4043]">
            <li>
              • <strong className="text-[#137333]">Aceleración % y Debuts (NEW):</strong> saltos porcentuales 7D en Spotify y YouTube, más entradas nuevas en Billboard o Top 200.
            </li>
            <li>
              • <strong className="text-[#B06000]">TikTok Multi-País & Instagram Reels 7D:</strong> tasa de crecimiento semanal en usos de sonido, videos de Explore y difusión simultánea en US/GB/MX/ES/BR/DE.
            </li>
            <li>
              • <strong className="text-[#007B83]">Radar Viral Temprano:</strong> posición alta en <em>Spotify Viral 50 Global</em> y <em>Shazam Global Viral 50</em>, los dos mejores predictores antes del pico mainstream.
            </li>
            <li>
              • <strong className="text-[#C5221F]">Frescura de lanzamiento:</strong> impulso extra para canciones publicadas o recién llegadas hace menos de 3 semanas.
            </li>
          </ul>
        </div>
      </section>

      {/* 5 Apify Paid Sources */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Flame className="h-5 w-5 text-[#E37400]" />
            <h3 className="font-display text-lg font-extrabold text-[#202124]">
              5 Actores Apify · Inteligencia Social y Viral
            </h3>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#FEF7E0] px-3 py-1 text-xs font-bold text-[#B06000]">
            <CreditCard className="h-3.5 w-3.5" />
            Fuentes de pago · Actualización semanal
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {APIFY_SOURCE_DOCS.map((doc) => (
            <SourceDocCard
              key={doc.id}
              doc={doc}
              badgeLabel={`De pago · ${doc.cadence}`}
              live={statusMap.get(doc.id)}
              snapshotMode={snapshot.mode}
            />
          ))}
        </div>
      </section>

      {/* 9 Free Sources */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-[#1E8E3E]" />
            <h3 className="font-display text-lg font-extrabold text-[#202124]">
              9 Fuentes Globales Gratuitas
            </h3>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#E6F4EA] px-3 py-1 text-xs font-bold text-[#137333]">
            <Headphones className="h-3.5 w-3.5" />
            Incluye enrichment automático de previews de 30s (iTunes + Deezer)
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {FREE_SOURCE_DOCS.map((doc) => (
            <SourceDocCard
              key={doc.id}
              doc={doc}
              badgeLabel={`Gratuita · ${doc.cadence}`}
              live={statusMap.get(doc.id)}
              snapshotMode={snapshot.mode}
            />
          ))}
        </div>
      </section>

      {/* Read-Only Weekly Sync Notice */}
      <section className="md-card flex flex-col gap-3 rounded-3xl border-[#CEEAD6] bg-[#E6F4EA]/50 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#1E8E3E] text-white">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <h4 className="font-display text-sm font-bold text-[#0D652D]">
              Actualización automática semanal
            </h4>
            <p className="mt-0.5 text-xs leading-relaxed text-[#137333]">
              TrendPulse sincroniza sus rankings cada miércoles a las 00:00 (UTC-5) de forma automatizada. Esta vista web pública es exclusivamente de solo lectura.
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-bold text-[#137333] shadow-xs">
          <Sparkles className="h-3.5 w-3.5" />
          Solo lectura
        </div>
      </section>
    </div>
  );
}
