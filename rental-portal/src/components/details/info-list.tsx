/**
 * Label / value list used in the side panel of a detail page.
 *
 * Values are right aligned and tabular, so a column of amounts or dates reads as
 * a table without the visual weight of one.
 */

"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export interface InfoListItem {
  label: string;
  value: ReactNode;
}

export function InfoList({
  items,
  className,
}: {
  items: InfoListItem[];
  className?: string;
}) {
  return (
    <dl className={cn("divide-border divide-y text-sm", className)}>
      {items.map(({ label, value }) => (
        <div
          key={label}
          className="flex items-start justify-between gap-4 py-2.5 first:pt-0 last:pb-0"
        >
          <dt className="text-muted-foreground shrink-0">{label}</dt>
          <dd className="text-right font-medium break-words tabular-nums">
            {value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
