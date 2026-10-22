/**
 * Maps the public property payload (`utility_billing.api.properties`) onto the
 * shared `PropertyView` used by the property card and row.
 */

import type { PropertyView } from "@/components/properties";
import { availabilityTone } from "@/components/properties";

export interface PublicPropertyFeature {
  feature: string;
  feature_type?: string;
  notes?: string;
}

export interface PublicPropertyImage {
  image: string;
  title?: string;
  description?: string;
}

/** Shape returned by `utility_billing.api.properties.get_available_properties`. */
export interface AvailableProperty {
  name: string;
  property_name: string;
  utility_category: string | null;
  company: string | null;
  status: string | null;
  location: string | null;
  territory: string | null;
  house_no: string | null;
  plot_no: string | null;
  unit_number: string | null;
  unit_type: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  unit_size: number | null;
  floor_level: string | null;
  cover_image: string | null;
  image_gallery?: PublicPropertyImage[];
  features?: PublicPropertyFeature[];
  parent_utility_property: string | null;
}

/** Build the subtitle from the address-ish parts of a property. */
function buildSubtitle(property: AvailableProperty): string | null {
  return (
    [
      property.unit_type,
      property.house_no,
      property.plot_no,
      property.location || property.territory,
    ]
      .filter(Boolean)
      .join(" · ") || null
  );
}

export function toAvailablePropertyView(
  property: AvailableProperty,
): PropertyView {
  const title = property.property_name || property.name;
  const image = property.cover_image || property.image_gallery?.[0]?.image || null;

  const specs = [
    property.bedrooms ? { icon: "bed" as const, label: `${property.bedrooms}` } : null,
    property.bathrooms
      ? { icon: "bath" as const, label: `${property.bathrooms}` }
      : null,
    property.unit_size
      ? { icon: "size" as const, label: `${property.unit_size} sqft` }
      : null,
    property.floor_level
      ? { icon: "floor" as const, label: property.floor_level }
      : null,
    property.utility_category
      ? { icon: "category" as const, label: property.utility_category }
      : null,
    property.parent_utility_property
      ? { icon: "building" as const, label: property.parent_utility_property }
      : null,
  ].filter(Boolean) as PropertyView["specs"];

  const featureTags = (property.features ?? [])
    .map((feature) => feature.feature)
    .filter(Boolean);

  return {
    id: property.name,
    title,
    subtitle: buildSubtitle(property),
    image,
    statusLabel: property.status,
    statusTone: availabilityTone(property.status),
    specs,
    tags: featureTags.slice(0, 4),
    href: `/properties/${encodeURIComponent(property.name)}`,
  };
}
