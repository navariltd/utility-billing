/**
 * Shared view model for the property list and "My Properties" pages.
 *
 * Both pages render the same card/row components, so each page only maps its own
 * API payload onto `PropertyView` (see `toAvailablePropertyView` and
 * `toTenantPropertyView`).
 */

/** How the property collection is rendered. */
export type PropertyLayout = "grid" | "list";

/** A short specification shown with an icon (bedrooms, size, ...). */
export interface PropertySpec {
  label: string;
  icon: "bed" | "bath" | "size" | "floor" | "building" | "category";
}

/** A labelled detail line (contract number, tenancy period, ...). */
export interface PropertyMeta {
  label: string;
  icon: "contract" | "calendar" | "location";
  badge?: string;
}

/** Tone used to colour the status badge. */
export type PropertyStatusTone =
  | "available"
  | "occupied"
  | "reserved"
  | "maintenance"
  | "history"
  | "neutral";

/** Normalised property used by `PropertyCard`, `PropertyRow` and `PropertyMedia`. */
export interface PropertyView {
  id: string;
  title: string;
  subtitle?: string | null;
  image?: string | null;
  statusLabel?: string | null;
  statusTone?: PropertyStatusTone;
  specs?: PropertySpec[];
  tags?: string[];
  meta?: PropertyMeta[];
  /** Detail page for the property, when one exists. */
  href?: string | null;
  footnote?: string | null;
}
