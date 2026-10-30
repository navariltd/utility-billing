/**
 * Card used for a section of a detail page (items, taxes, meter readings).
 *
 * The header carries an optional icon, a description and an action slot (a
 * count pill, a link); the content stays unpadded by default so tables can run
 * edge to edge.
 */

"use client";

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function SectionCard({
  title,
  description,
  icon: Icon,
  action,
  children,
  className,
  contentClassName,
}: {
  title: string;
  description?: ReactNode;
  icon?: LucideIcon;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <Card className={cn("gap-0 overflow-hidden rounded-xl py-0", className)}>
      <CardHeader className="px-4 py-3.5 sm:px-5">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          {Icon ? <Icon className="text-muted-foreground size-4" /> : null}
          {title}
        </CardTitle>
        {description ? (
          <CardDescription className="text-xs">{description}</CardDescription>
        ) : null}
        {action ? <CardAction>{action}</CardAction> : null}
      </CardHeader>
      <CardContent className={cn("border-t p-0", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  );
}

/** Count pill shown in a `SectionCard` action slot. */
export function CountPill({ children }: { children: ReactNode }) {
  return (
    <span className="bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-xs font-medium tabular-nums">
      {children}
    </span>
  );
}
