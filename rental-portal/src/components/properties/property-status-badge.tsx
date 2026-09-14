/**
 * Status badge for a property (availability or tenancy state).
 */

"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Clock, History, Home } from "lucide-react";

import type { PropertyStatusTone } from "./types";

const TONE_STYLES: Record<PropertyStatusTone, string> = {
  available: "border-green-200 bg-green-100 text-green-800",
  occupied: "border-blue-200 bg-blue-100 text-blue-800",
  reserved: "border-amber-200 bg-amber-100 text-amber-800",
  maintenance: "border-orange-200 bg-orange-100 text-orange-800",
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
