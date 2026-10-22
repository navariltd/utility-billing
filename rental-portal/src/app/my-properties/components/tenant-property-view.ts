/**
 * Maps a tenant property allocation onto the shared `PropertyView`.
 */

import { tenancyTone, type PropertyView } from "@/components/properties";
import type { TenantProperty } from "@/types/portal";

function formatDate(value: string | null): string | null {
  if (!value) return null;

  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function toTenantPropertyView(property: TenantProperty): PropertyView {
  const subtitle =
    [property.unit_number, property.unit_type, property.location]
      .filter(Boolean)
      .join(" · ") || property.utility_property;

  const period = [formatDate(property.start_date), formatDate(property.end_date)]
    .filter(Boolean)
    .join(" → ");

  const specs = [
    property.bedrooms ? { icon: "bed" as const, label: `${property.bedrooms}` } : null,
    property.bathrooms
      ? { icon: "bath" as const, label: `${property.bathrooms}` }
      : null,
    property.unit_size
      ? { icon: "size" as const, label: `${property.unit_size}` }
      : null,
    property.floor_level
      ? { icon: "floor" as const, label: property.floor_level }
      : null,
    property.parent_utility_property
      ? { icon: "building" as const, label: property.parent_utility_property }
      : null,
  ].filter(Boolean) as PropertyView["specs"];

  return {
    id: `${property.contract}-${property.utility_property}`,
    title: property.property_name,
    subtitle,
    image: property.cover_image,
    statusLabel: property.state,
    statusTone: tenancyTone(property.state),
    specs,
    meta: [
      {
        icon: "contract",
        label: property.contract,
        badge:
          property.contract_status || (property.is_signed ? "Signed" : "Unsigned"),
      },
      ...(period ? [{ icon: "calendar" as const, label: period }] : []),
    ],
    href: `/properties/${encodeURIComponent(property.utility_property)}`,
    footnote:
      property.state === "Reserved"
        ? "Reserved for you until the tenancy agreement is signed."
        : null,
  };
}
