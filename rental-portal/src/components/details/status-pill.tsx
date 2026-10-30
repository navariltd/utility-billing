/**
 * Tone aware status pill used by the document and meter reading pages.
 *
 * The tones reuse the semantic theme tokens (`success`, `warning`,
 * `destructive`, `info`), so a pill follows the active theme preset instead of
 * hard coding colours. The dot doubles as the state indicator, which keeps the
 * pill readable without an icon.
 */

"use client";

import { cn } from "@/lib/utils";

import type { StatusTone } from "./status-tones";

const TONE_STYLES: Record<StatusTone, string> = {
  success: "border-success/25 bg-success/10 text-success",
  warning: "border-warning/25 bg-warning/10 text-warning",
  danger: "border-destructive/25 bg-destructive/10 text-destructive",
  info: "border-info/25 bg-info/10 text-info",
  primary: "border-primary/25 bg-primary/10 text-primary",
  neutral: "border-border bg-muted text-muted-foreground",
};

export function StatusPill({
  label,
  tone = "neutral",
  className,
}: {
  label: string;
  tone?: StatusTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        TONE_STYLES[tone],
        className,
      )}
    >
      <span aria-hidden className="size-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
