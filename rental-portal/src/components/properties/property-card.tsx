/**
 * Grid card for a property (used in the `grid` layout of both property pages).
 */

"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { PropertyMedia } from "./property-media";
import { PropertyMetaList, PropertySpecs } from "./property-specs";
import { PropertyStatusBadge } from "./property-status-badge";
import type { PropertyView } from "./types";

export function PropertyCard({ property }: { property: PropertyView }) {
  const body = (
    <Card className="group h-full gap-0 overflow-hidden pt-0">
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-muted">
        <PropertyMedia src={property.image} name={property.title} variant="cover" />
        {property.statusLabel ? (
          <div className="absolute top-3 left-3">
            <PropertyStatusBadge
              label={property.statusLabel}
              tone={property.statusTone}
              className="bg-background/90 backdrop-blur"
            />
          </div>
        ) : null}
      </div>
      <CardHeader className="gap-1 pt-4">
        <h3 className="truncate text-base font-semibold">{property.title}</h3>
        {property.subtitle ? (
          <p className="text-muted-foreground truncate text-sm">{property.subtitle}</p>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        <PropertySpecs specs={property.specs} />
        {property.tags?.length ? (
          <div className="flex flex-wrap gap-1">
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
        <PropertyMetaList meta={property.meta} className="text-muted-foreground" />
        {property.footnote ? (
          <p className="text-muted-foreground text-xs">{property.footnote}</p>
        ) : null}
        {property.href ? (
          <span className="text-primary mt-auto inline-flex items-center gap-1 pt-1 text-sm font-medium">
            View details
            <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </span>
        ) : null}
      </CardContent>
    </Card>
  );

  return property.href ? (
    <Link to={property.href} className="block h-full focus-visible:outline-none">
      {body}
    </Link>
  ) : (
    body
  );
}
