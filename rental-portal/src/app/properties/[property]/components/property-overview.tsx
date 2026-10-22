/**
 * Property overview – status, title, specifications, amenities and description.
 */

"use client";

import { PropertySpecs, PropertyStatusBadge } from "@/components/properties";
import type { PropertySpec } from "@/components/properties";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PropertyDetails } from "@/types/property-details";
import { availabilityTone } from "@/components/properties";

/**
 * Strip markup from rich text fields (they are rendered as plain text because
 * this page is reachable by guests).
 */
export function toPlainText(html?: string | null): string {
  if (!html) return "";

  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|li)>/gi, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function buildSpecs(property: PropertyDetails): PropertySpec[] {
  return [
    property.bedrooms ? { icon: "bed" as const, label: `${property.bedrooms} bedrooms` } : null,
    property.bathrooms
      ? { icon: "bath" as const, label: `${property.bathrooms} bathrooms` }
      : null,
    property.unit_size ? { icon: "size" as const, label: `${property.unit_size} sqft` } : null,
    property.floor_level ? { icon: "floor" as const, label: property.floor_level } : null,
    property.utility_category
      ? { icon: "category" as const, label: property.utility_category }
      : null,
    property.parent_utility_property
      ? { icon: "building" as const, label: property.parent_utility_property }
      : null,
  ].filter(Boolean) as PropertySpec[];
}

function buildAddress(property: PropertyDetails): string {
  return [
    property.house_no,
    property.plot_no,
    property.location || property.territory,
  ]
    .filter(Boolean)
    .join(", ");
}

export function PropertyOverview({ property }: { property: PropertyDetails }) {
  const address = buildAddress(property);
  const description = toPlainText(property.unique_features);
  const legal = toPlainText(property.legal_description);

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <PropertyStatusBadge
            label={property.status || "Unknown"}
            tone={availabilityTone(property.status)}
          />
          {property.unit_type ? (
            <span className="text-muted-foreground text-sm">{property.unit_type}</span>
          ) : null}
        </div>
        <h1 className="text-2xl font-bold tracking-tight">
          {property.property_name || property.name}
        </h1>
        {address ? <p className="text-muted-foreground text-sm">{address}</p> : null}
        <PropertySpecs specs={buildSpecs(property)} className="pt-1" />
      </div>

      {description ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">About this property</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground text-sm whitespace-pre-line">
            {description}
          </CardContent>
        </Card>
      ) : null}

      {property.features?.length ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Features and amenities</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {property.features.map((feature) => (
              <span
                key={`${feature.feature}-${feature.feature_type ?? ""}`}
                className="bg-muted rounded-full px-3 py-1 text-xs"
                title={feature.notes ?? undefined}
              >
                {feature.feature}
                {feature.feature_type ? (
                  <span className="text-muted-foreground"> · {feature.feature_type}</span>
                ) : null}
              </span>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {legal ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Legal description</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground text-sm whitespace-pre-line">
            {legal}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
