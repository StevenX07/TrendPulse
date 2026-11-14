import type { SourceStatus, WeeklySnapshot } from "../types/trends";

/**
 * Determine whether a source failed or was omitted unexpectedly (e.g., quota / API error)
 * rather than being intentionally inactive in a free-only snapshot.
 */
export function isSourceIssue(
  source: SourceStatus,
  snapshotMode: "free" | "full",
): boolean {
  if (source.status === "error") return true;
  if (source.status !== "skipped") return false;
  if (snapshotMode === "full") return true;
  const note = (source.note || "").toLowerCase();
  return (
    note.includes("insuficiente") ||
    note.includes("agotad") ||
    note.includes("cuota") ||
    note.includes("límite") ||
    note.includes("no disponible") ||
    note.includes("error") ||
    note.includes("fallo")
  );
}

/** Return all sources from a snapshot that failed or were unavailable unexpectedly. */
export function getProblemSources(snapshot: WeeklySnapshot): SourceStatus[] {
  return (snapshot.sources || []).filter((s) => isSourceIssue(s, snapshot.mode));
}
