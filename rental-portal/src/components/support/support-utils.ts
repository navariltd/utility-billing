/** Presentation helpers for support tickets. */

import type { SupportIssueStatus } from "@/types/support";

const STATUS_STYLES: Record<SupportIssueStatus, string> = {
  Open: "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950/50 dark:text-sky-300",
  Replied:
    "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950/50 dark:text-violet-300",
  "On Hold":
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300",
  Resolved:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-300",
  Closed: "border-border bg-muted text-muted-foreground",
};

const PRIORITY_STYLES: Record<string, string> = {
  low: "bg-sky-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  urgent: "bg-red-500",
};

/** Return badge classes for an Issue status. */
export function supportStatusClass(status: SupportIssueStatus): string {
  return STATUS_STYLES[status] ?? STATUS_STYLES.Open;
}

/** Return a dot colour for an Issue priority. */
export function supportPriorityDot(priority?: string | null): string {
  return PRIORITY_STYLES[(priority ?? "").toLowerCase()] ?? "bg-muted-foreground/50";
}

/** Format a Frappe Duration value (stored in seconds) for display. */
export function formatSupportDuration(
  value?: number | string | null,
): string {
  const seconds = Number(value ?? 0);
  if (!Number.isFinite(seconds) || seconds <= 0) return "—";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return "< 1 min";
  if (minutes < 60) return `${minutes} min`;

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours < 24) {
    return remainingMinutes ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  }

  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return remainingHours ? `${days}d ${remainingHours}h` : `${days}d`;
}

/** Return up to two initials for a display name. */
export function supportInitials(name?: string | null): string {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}
