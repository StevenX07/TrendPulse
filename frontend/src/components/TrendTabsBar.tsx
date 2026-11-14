import {
  Database,
  Flame,
  Globe,
  Headphones,
  Layers,
  Rocket,
  Search,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";
import type { PlatformFilter, TrendTab } from "../types/trends";

interface TrendTabsBarProps {
  activeTab: TrendTab;
  onChangeTab: (tab: TrendTab) => void;
  platformFilter: PlatformFilter;
  onChangePlatformFilter: (pf: PlatformFilter) => void;
  searchQuery: string;
  onChangeSearch: (q: string) => void;
  onlyPlayable: boolean;
  onToggleOnlyPlayable: () => void;
  onlyMultiPlatform: boolean;
  onToggleOnlyMultiPlatform: () => void;
  resultCount: number;
}

const TABS: Array<{
  id: TrendTab;
  label: string;
  icon: typeof TrendingUp;
  activeClass: string;
}> = [
  {
    id: "most_streamed",
    label: "Más Streameadas (7D)",
    icon: TrendingUp,
    activeClass: "bg-[#1A73E8] text-white shadow-xs",
  },
  {
    id: "fastest_growth",
    label: "Crecimiento Rápido",
    icon: Rocket,
    activeClass: "bg-[#1E8E3E] text-white shadow-xs",
  },
  {
    id: "tiktok_viral",
    label: "TikTok & Reels",
    icon: Flame,
    activeClass: "bg-[#E37400] text-white shadow-xs",
  },
  {
    id: "new_breakouts",
    label: "Recién Llegadas",
    icon: Sparkles,
    activeClass: "bg-[#D93025] text-white shadow-xs",
  },
  {
    id: "platform_radar",
    label: "Radar por Plataforma",
    icon: Globe,
    activeClass: "bg-[#202124] text-white shadow-xs",
  },
  {
    id: "sources",
    label: "Fuentes",
    icon: Database,
    activeClass: "bg-[#1967D2] text-white shadow-xs",
  },
];

const PLATFORM_PILLS: Array<{ id: PlatformFilter; label: string }> = [
  { id: "all", label: "Todas" },
  { id: "spotify", label: "Spotify 7D" },
  { id: "spotify_viral", label: "Spotify Viral 50" },
  { id: "youtube", label: "YouTube 7D" },
  { id: "reels", label: "Instagram Reels" },
  { id: "shazam", label: "Shazam Global/Viral" },
  { id: "apple", label: "Apple Music" },
  { id: "billboard", label: "Billboard Hot 100" },
];

export function TrendTabsBar({
  activeTab,
  onChangeTab,
  platformFilter,
  onChangePlatformFilter,
  searchQuery,
  onChangeSearch,
  onlyPlayable,
  onToggleOnlyPlayable,
  onlyMultiPlatform,
  onToggleOnlyMultiPlatform,
  resultCount,
}: TrendTabsBarProps) {
  const isSourcesTab = activeTab === "sources";

  return (
    <section className="space-y-3">
      {/* Main Tabs + Search */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2 rounded-3xl bg-[#F1F3F4] p-1.5">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => onChangeTab(tab.id)}
                className={`flex cursor-pointer items-center gap-1.5 rounded-full px-3.5 py-2 font-display text-xs font-bold transition sm:text-sm ${
                  active
                    ? tab.activeClass
                    : "text-[#5F6368] hover:bg-white/80 hover:text-[#202124]"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Search Input Pill */}
        {!isSourcesTab && (
          <div className="relative w-full lg:w-72">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#5F6368]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onChangeSearch(e.target.value)}
              placeholder="Buscar canción, artista o género..."
              className="w-full rounded-full border border-[#DADCE0] bg-white py-2 pl-10 pr-9 text-sm text-[#202124] placeholder-[#80868B] transition focus:border-[#1A73E8] focus:outline-none focus:ring-2 focus:ring-[#D2E3FC]"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => onChangeSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer rounded-full p-0.5 text-[#5F6368] hover:bg-[#F1F3F4]"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Sub-filters & Result Counter */}
      {!isSourcesTab && (
        <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {activeTab === "platform_radar" &&
            PLATFORM_PILLS.map((pill) => {
              const selected = platformFilter === pill.id;
              return (
                <button
                  key={pill.id}
                  type="button"
                  onClick={() => onChangePlatformFilter(pill.id)}
                  className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-semibold transition ${
                    selected
                      ? "border-[#1A73E8] bg-[#E8F0FE] text-[#1967D2]"
                      : "border-[#DADCE0] bg-white text-[#5F6368] hover:bg-[#F1F3F4]"
                  }`}
                >
                  {pill.label}
                </button>
              );
            })}

          <button
            type="button"
            onClick={onToggleOnlyPlayable}
            className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition ${
              onlyPlayable
                ? "border-[#1A73E8] bg-[#E8F0FE] text-[#1967D2]"
                : "border-[#DADCE0] bg-white text-[#5F6368] hover:bg-[#F1F3F4]"
            }`}
          >
            <Headphones className="h-3.5 w-3.5" />
            <span>Con preview</span>
          </button>

          <button
            type="button"
            onClick={onToggleOnlyMultiPlatform}
            className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition ${
              onlyMultiPlatform
                ? "border-[#1E8E3E] bg-[#E6F4EA] text-[#137333]"
                : "border-[#DADCE0] bg-white text-[#5F6368] hover:bg-[#F1F3F4]"
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>3+ plataformas</span>
          </button>
        </div>

        <span className="text-xs font-medium text-[#5F6368]">
          Mostrando <strong className="font-display text-[#202124]">{resultCount}</strong> canciones
        </span>
      </div>
      )}
    </section>
  );
}
