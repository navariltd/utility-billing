/**
 * Hero of a detail page: the icon and eyebrow of the document type, its title,
 * the status pills, a row of metadata and an optional aside (amount and action).
 *
 * The gradient and dot texture are decorative only; they use theme tokens so
 * the hero follows the active colour preset. The hero carries the page `h1`, so
 * detail pages pass no `title` to `BaseLayout`.
 */

"use client";

import { Card } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export interface DetailHeroMeta {
  icon: LucideIcon;
  label: ReactNode;
}

export function DetailHero({
  icon: Icon,
  eyebrow,
  title,
  description,
  badges,
  meta = [],
  aside,
}: {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  description?: ReactNode;
  badges?: ReactNode;
  meta?: DetailHeroMeta[];
  aside?: ReactNode;
}) {
  return (
    <Card className="relative gap-0 overflow-hidden rounded-2xl py-0 shadow-sm">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-16 -right-10 size-48 bg-[radial-gradient(circle,var(--color-foreground)_1px,transparent_1px)] [background-size:14px_14px] opacity-[0.06]"
      />

      <div className="relative flex flex-col gap-6 p-5 sm:p-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="text-muted-foreground flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.16em] uppercase">
            <span className="bg-primary/10 text-primary ring-primary/15 flex size-8 items-center justify-center rounded-lg ring-1">
              <Icon className="size-4" />
            </span>
            {eyebrow}
          </div>

          <div className="space-y-2">
            <h1 className="truncate text-xl font-semibold tracking-tight tabular-nums sm:text-2xl">
              {title}
            </h1>
            {description ? (
              <p className="text-muted-foreground text-sm">{description}</p>
            ) : null}
            {badges ? (
              <div className="flex flex-wrap items-center gap-2">{badges}</div>
            ) : null}
          </div>

          {meta.length ? (
            <ul className="text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
              {meta.map(({ icon: MetaIcon, label }, index) => (
                <li key={index} className="flex items-center gap-1.5">
                  <MetaIcon className="size-3.5 opacity-70" />
                  <span className="text-foreground/80">{label}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        {aside ? (
          <div className="shrink-0 space-y-3 lg:text-right">{aside}</div>
        ) : null}
      </div>
    </Card>
  );
}
