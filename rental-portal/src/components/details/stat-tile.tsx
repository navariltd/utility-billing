/**
 * Compact metric tile used in the KPI strip of a detail page.
 *
 * The icon sits in a tinted square whose tone matches the meaning of the value
 * (`danger` for money due, `info` for neutral figures), which makes the strip
 * scannable without extra labels.
 */

"use client";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import type { StatusTone } from "./status-tones";

const TONE_STYLES: Record<StatusTone, string> = {
  success: "bg-success/10 text-success ring-success/15",
  warning: "bg-warning/10 text-warning ring-warning/15",
  danger: "bg-destructive/10 text-destructive ring-destructive/15",
  info: "bg-info/10 text-info ring-info/15",
  primary: "bg-primary/10 text-primary ring-primary/15",
  neutral: "bg-muted text-muted-foreground ring-border",
};

export function StatTile({
  label,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon: LucideIcon;
  tone?: StatusTone;
  className?: string;
}) {
  return (
    <Card className={cn("gap-0 rounded-xl p-4 shadow-none", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
            {label}
          </p>
          <p className="truncate text-lg font-semibold tabular-nums sm:text-xl">
            {value}
          </p>
        </div>
        <span
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-lg ring-1",
            TONE_STYLES[tone],
          )}
        >
          <Icon className="size-4" />
        </span>
      </div>
      {hint ? (
        <p className="text-muted-foreground mt-2 truncate text-xs">{hint}</p>
      ) : null}
    </Card>
  );
}
