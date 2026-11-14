import { AlertTriangle, Calendar, CheckCircle2, Waves } from "lucide-react";
import type { HistoryWeekEntry, WeeklySnapshot } from "../types/trends";
import { formatIsoDateLocal } from "../utils/format";
import { getProblemSources } from "../utils/sources";

interface TopAppBarProps {
  snapshot: WeeklySnapshot;
  historyWeeks: HistoryWeekEntry[];
  selectedWeekId: string;
  onSelectWeek: (weekId: string) => void;
  onOpenSourcesInfo: () => void;
}

export function TopAppBar({
  snapshot,
  historyWeeks,
  selectedWeekId,
  onSelectWeek,
  onOpenSourcesInfo,
}: TopAppBarProps) {
  const totalOk = snapshot.summary.free_sources_ok + snapshot.summary.apify_sources_ok;
  const problemCount = getProblemSources(snapshot).length;

  return (
    <header className="relative z-30 border-b border-[#E8EAED] bg-white/95 backdrop-blur-md md:sticky md:top-0">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2.5 px-3.5 py-2.5 sm:px-6 sm:py-3">
        {/* Brand Identity */}
        <div className="flex min-w-0 items-center gap-2.5 sm:gap-3">
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-[#E8F0FE] text-[#1A73E8] shadow-xs sm:h-11 sm:w-11">
            <Waves className="h-5 w-5 stroke-[2.4] sm:h-6 sm:w-6" />
            <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5 sm:h-3 sm:w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#34A853] opacity-60" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full border-2 border-white bg-[#1E8E3E] sm:h-3 sm:w-3" />
            </span>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="font-display text-lg font-extrabold tracking-tight text-[#202124] sm:text-2xl">
                Trend<span className="text-[#1A73E8]">Pulse</span>
              </h1>
              <span className="hidden rounded-full bg-[#F1F3F4] px-2.5 py-0.5 text-[11px] font-semibold text-[#5F6368] sm:inline-block">
                7 Días · Global
              </span>
            </div>
            <p className="truncate text-[11px] text-[#5F6368] sm:text-xs">
              Última lectura: <span className="font-medium text-[#202124]">{formatIsoDateLocal(snapshot.generated_at)}</span>
              <span className="lg:hidden"> · Sync Mié 00:00</span>
            </p>
          </div>
        </div>

        {/* Right Action Pills */}
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          {/* Week Selector */}
          {historyWeeks.length > 0 && (
            <label className="flex items-center gap-1 rounded-full border border-[#DADCE0] bg-[#F8F9FA] px-2.5 py-1 text-[11px] font-medium text-[#3C4043] transition hover:bg-[#F1F3F4] sm:gap-1.5 sm:px-3 sm:py-1.5 sm:text-xs">
              <Calendar className="h-3 w-3 text-[#1A73E8] sm:h-3.5 sm:w-3.5" />
              <select
                aria-label="Seleccionar semana"
                value={selectedWeekId || snapshot.week_id}
                onChange={(e) => onSelectWeek(e.target.value)}
                className="cursor-pointer bg-transparent pr-0.5 font-medium text-[#202124] focus:outline-none sm:pr-1"
              >
                {historyWeeks.map((wk, i) => (
                  <option key={wk.week_id} value={wk.week_id}>
                    {wk.week_id} {i === 0 ? "(Actual)" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}

          {/* Sources Counter Pill */}
          <button
            type="button"
            onClick={onOpenSourcesInfo}
            className={`flex cursor-pointer items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium transition sm:gap-1.5 sm:px-3 sm:py-1.5 sm:text-xs ${
              problemCount > 0
                ? "border-[#FDD663] bg-[#FEF7E0] text-[#B06000] hover:bg-[#FEEFC3]"
                : "border-[#DADCE0] bg-white text-[#3C4043] hover:bg-[#F1F3F4]"
            }`}
            title="Ver detalle de fuentes e incidencias"
          >
            {problemCount > 0 ? (
              <AlertTriangle className="h-3 w-3 text-[#B06000] sm:h-3.5 sm:w-3.5" />
            ) : (
              <CheckCircle2 className="h-3 w-3 text-[#1E8E3E] sm:h-3.5 sm:w-3.5" />
            )}
            <span>
              {totalOk} fuentes
              {problemCount > 0 ? ` · ${problemCount}` : ""}
            </span>
          </button>

          <span className="hidden rounded-full bg-[#E6F4EA] px-3 py-1.5 text-xs font-semibold text-[#137333] lg:inline-flex">
            Auto-sync Mié 00:00 (UTC-5)
          </span>
        </div>
      </div>
    </header>
  );
}
