/** Shared property presentation components (card, row, media, layout switch). */

export { PropertyCard } from "./property-card";
export { PropertyRow } from "./property-row";
export { PropertyMedia, getInitials } from "./property-media";
export { PropertySpecs, PropertyMetaList } from "./property-specs";
export {
  PropertyStatusBadge,
  availabilityTone,
  tenancyTone,
} from "./property-status-badge";
export { LayoutToggle } from "./layout-toggle";
export type {
  PropertyLayout,
  PropertyMeta,
  PropertySpec,
  PropertyStatusTone,
  PropertyView,
} from "./types";
