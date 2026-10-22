/**
 * List row for a property (used in the `list` layout of both property pages).
 */

"use client";

import { Card, CardContent } from "@/components/ui/card";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { PropertyMedia } from "./property-media";
import { PropertyMetaList, PropertySpecs } from "./property-specs";
import { PropertyStatusBadge } from "./property-status-badge";
import type { PropertyView } from "./types";

export function PropertyRow({ property }: { property: PropertyView }) {
  const body = (
    <Card className="group gap-0 overflow-hidden py-0">
      <CardContent className="flex items-center gap-4 p-3 sm:p-4">
        <div className="h-20 w-24 shrink-0 overflow-hidden rounded-lg bg-muted sm:h-24 sm:w-32">
          <PropertyMedia src={property.image} name={property.title} variant="cover" />
        </div>

        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-sm font-semibold sm:text-base">
              {property.title}
            </h3>
            {property.statusLabel ? (
              <PropertyStatusBadge
                label={property.statusLabel}
                tone={property.statusTone}
              />
            ) : null}
          </div>

          {property.subtitle ? (
            <p className="text-muted-foreground truncate text-xs sm:text-sm">
              {property.subtitle}
            </p>
          ) : null}

          <PropertySpecs specs={property.specs} size="sm" />
          <PropertyMetaList meta={property.meta} className="text-muted-foreground" />

          {property.tags?.length ? (
            <div className="hidden flex-wrap gap-1 sm:flex">
              {property.tags.map((tag) => (
                <span
                  key={tag}
                  className="bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-[11px]"
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}

          {property.footnote ? (
            <p className="text-muted-foreground text-xs">{property.footnote}</p>
          ) : null}
        </div>

        {property.href ? (
          <ArrowUpRight className="text-muted-foreground group-hover:text-primary h-4 w-4 shrink-0 transition-colors" />
        ) : null}
      </CardContent>
    </Card>
  );

  return property.href ? (
    <Link to={property.href} className="block focus-visible:outline-none">
      {body}
    </Link>
  ) : (
    body
  );
}
