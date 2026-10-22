/**
 * Specification and meta rows shared by the property card and row.
 */

"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Bath,
  Bed,
  Building2,
  CalendarDays,
  FileSignature,
  Layers,
  MapPin,
  Ruler,
  Tags,
} from "lucide-react";

import type { PropertyMeta, PropertySpec } from "./types";

const SPEC_ICONS = {
  bed: Bed,
  bath: Bath,
  size: Ruler,
  floor: Layers,
  building: Building2,
  category: Tags,
} as const;

const META_ICONS = {
  contract: FileSignature,
  calendar: CalendarDays,
  location: MapPin,
} as const;

interface PropertySpecsProps {
  specs?: PropertySpec[];
  className?: string;
  /** `sm` is used inside list rows, `md` on cards. */
  size?: "sm" | "md";
}

/** Inline specification list (bedrooms, bathrooms, size, floor, ...). */
export function PropertySpecs({
  specs = [],
  className,
  size = "md",
}: PropertySpecsProps) {
  if (specs.length === 0) return null;

  const iconClass = size === "sm" ? "h-3 w-3" : "h-4 w-4";

  return (
    <div
      className={cn(
        "text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1 text-xs",
        className,
      )}
    >
      {specs.map((spec) => {
        const Icon = SPEC_ICONS[spec.icon];
        return (
          <span key={`${spec.icon}-${spec.label}`} className="flex items-center gap-1">
            <Icon className={iconClass} />
            {spec.label}
          </span>
        );
      })}
    </div>
  );
}

/** Meta lines shown under a card/row (contract reference, dates, location). */
export function PropertyMetaList({
  meta = [],
  className,
}: {
  meta?: PropertyMeta[];
  className?: string;
}) {
  if (meta.length === 0) return null;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-2 text-xs",
        className,
      )}
    >
      {meta.map((item) => {
        const Icon = META_ICONS[item.icon];
        return (
          <span key={`${item.icon}-${item.label}`} className="flex items-center gap-1">
            <Icon className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{item.label}</span>
            {item.badge ? (
              <Badge variant="secondary" className="ml-1 text-[10px]">
                {item.badge}
              </Badge>
            ) : null}
          </span>
        );
      })}
    </div>
  );
}
