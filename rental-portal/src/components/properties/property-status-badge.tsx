/**
 * Status badge for a property (availability or tenancy state).
 *
 * Tones are expressed with theme tokens so the badge follows the active theme
 * preset: `primary` for occupied units, `success`/`warning`/`info` for the
 * remaining states and `muted` for historical entries.
 */

"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Clock, History, Home } from "lucide-react";

import type { PropertyStatusTone } from "./types";

const TONE_STYLES: Record<PropertyStatusTone, string> = {
  available: "border-success/30 bg-success/15 text-success",
  occupied: "border-primary/30 bg-primary/10 text-primary",
  reserved: "border-info/30 bg-info/15 text-info",
  maintenance: "border-warning/30 bg-warning/15 text-warning",
  history: "border-border bg-muted text-muted-foreground",
  neutral: "border-border bg-muted text-muted-foreground",
};

const TONE_ICONS: Partial<Record<PropertyStatusTone, typeof CheckCircle2>> = {
  available: CheckCircle2,
  occupied: Home,
  reserved: AlertCircle,
  maintenance: Clock,
  history: History,
};

interface PropertyStatusBadgeProps {
  label: string;
  tone?: PropertyStatusTone;
  className?: string;
}

export function PropertyStatusBadge({
  label,
  tone = "neutral",
  className,
}: PropertyStatusBadgeProps) {
  const Icon = TONE_ICONS[tone];

  return (
    <Badge
      variant="outline"
      className={cn("gap-1 whitespace-nowrap", TONE_STYLES[tone], className)}
    >
      {Icon ? <Icon className="h-3 w-3" /> : null}
      {label}
    </Badge>
  );
}

/** Map the property availability values to badge tones. */
export function availabilityTone(status?: string | null): PropertyStatusTone {
  switch (status) {
    case "Available":
      return "available";
    case "Occupied":
      return "occupied";
    case "Reserved":
      return "reserved";
    case "Under Maintenance":
      return "maintenance";
    default:
      return "neutral";
  }
}

/** Map the tenancy state of a contract allocation to badge tones. */
export function tenancyTone(state?: string | null): PropertyStatusTone {
  switch (state) {
    case "Active":
      return "available";
    case "Reserved":
      return "reserved";
    case "History":
      return "history";
    default:
      return "neutral";
  }
}
