export function formatCompactNumber(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  const abs = Math.abs(val);
  if (abs >= 1_000_000_000) return `${(val / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(val / 1_000).toFixed(1)}K`;
  return val.toLocaleString("es-ES");
}

export function formatSignedCompact(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val) || val === 0) return "0";
  const prefix = val > 0 ? "+" : "";
  return `${prefix}${formatCompactNumber(val)}`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds <= 0) return "";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function formatIsoDateLocal(iso: string): string {
  if (!iso) return "Sin fecha";
  try {
    const dt = new Date(iso);
    return dt.toLocaleString("es-CO", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
