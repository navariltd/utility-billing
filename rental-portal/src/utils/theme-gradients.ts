/**
 * CSS gradient builders for the themeable surfaces.
 *
 * Gradients are generated from the tokens of the active mode (via `var()`
 * references) so one gradient string blends correctly in both light and dark.
 * Every builder returns a plain CSS `background-image` value, which the theme
 * store writes to `--background-gradient`, `--sidebar-gradient` or
 * `--primary-gradient`.
 */

import type { GradientSurface } from "@/types/theme-customizer";

export type GradientVariant =
  | "none"
  | "sheen"
  | "diagonal"
  | "aurora"
  | "mesh"
  | "custom";

export interface GradientVariantOption {
  value: GradientVariant;
  label: string;
  description: string;
}

export const gradientVariants: GradientVariantOption[] = [
  { value: "none", label: "None", description: "Flat surface colour" },
  { value: "sheen", label: "Sheen", description: "Soft one direction wash" },
  { value: "diagonal", label: "Diagonal", description: "Two colour corner blend" },
  { value: "aurora", label: "Aurora", description: "Two corner glows" },
  { value: "mesh", label: "Mesh", description: "Three point colour mesh" },
  { value: "custom", label: "Custom", description: "Paste your own CSS gradient" },
];

/** How far a tint is mixed into the surface colour for a given surface. */
const INTENSITY: Record<GradientSurface, number> = {
  page: 1,
  sidebar: 1.7,
  brand: 1,
};

/** `color-mix` helper keeping the generated gradients readable. */
function mix(color: string, percent: number, into: string): string {
  const rounded = Math.round(Math.max(0, Math.min(100, percent)) * 10) / 10;
  return `color-mix(in oklab, ${color} ${rounded}%, ${into})`;
}

/** Surface colours used by the page and sidebar recipes. */
const SURFACE_TOKENS: Record<"page" | "sidebar", { base: string; primary: string; accent: string }> = {
  page: {
    base: "var(--background)",
    primary: "var(--primary)",
    accent: "var(--accent)",
  },
  sidebar: {
    base: "var(--sidebar)",
    primary: "var(--sidebar-primary)",
    accent: "var(--accent)",
  },
};

/** Build the gradient for a tinted surface (page or sidebar). */
function surfaceGradient(
  surface: "page" | "sidebar",
  variant: Exclude<GradientVariant, "custom">,
): string | undefined {
  const { base, primary, accent } = SURFACE_TOKENS[surface];
  const strength = INTENSITY[surface];

  switch (variant) {
    case "none":
      return undefined;
    case "sheen":
      return `linear-gradient(180deg, ${mix(primary, 7 * strength, base)} 0%, ${base} 45%, ${base} 100%)`;
    case "diagonal":
      return `linear-gradient(135deg, ${mix(primary, 15 * strength, base)} 0%, ${base} 52%, ${mix(accent, 11 * strength, base)} 100%)`;
    case "aurora":
      return [
        `radial-gradient(120% 90% at 0% 0%, ${mix(accent, 17 * strength, "transparent")} 0%, transparent 58%)`,
        `radial-gradient(110% 80% at 100% 0%, ${mix(primary, 16 * strength, "transparent")} 0%, transparent 55%)`,
      ].join(", ");
    case "mesh":
      return [
        `radial-gradient(80% 60% at 12% 8%, ${mix(accent, 20 * strength, "transparent")} 0%, transparent 60%)`,
        `radial-gradient(70% 60% at 88% 18%, ${mix(primary, 19 * strength, "transparent")} 0%, transparent 60%)`,
        `radial-gradient(90% 70% at 50% 100%, ${mix(primary, 13 * strength, "transparent")} 0%, transparent 65%)`,
      ].join(", ");
  }
}

/** Build the gradient used by the brand surface (primary backgrounds). */
function brandGradient(
  variant: Exclude<GradientVariant, "custom">,
): string | undefined {
  const primary = "var(--primary)";
  const accent = "var(--accent)";
  const strength = INTENSITY.brand;

  switch (variant) {
    case "none":
      return undefined;
    case "sheen":
      return `linear-gradient(160deg, ${primary} 0%, ${mix(accent, 28 * strength, primary)} 100%)`;
    case "diagonal":
      return `linear-gradient(135deg, ${primary} 0%, ${mix(accent, 55 * strength, primary)} 55%, ${primary} 100%)`;
    case "aurora":
      return [
        `radial-gradient(130% 110% at 0% 0%, ${mix(accent, 70 * strength, primary)} 0%, ${primary} 62%)`,
        `linear-gradient(160deg, ${primary} 0%, ${mix(accent, 30 * strength, primary)} 100%)`,
      ].join(", ");
    case "mesh":
      return [
        `radial-gradient(75% 70% at 0% 0%, ${mix(accent, 65 * strength, "transparent")} 0%, transparent 60%)`,
        `radial-gradient(70% 70% at 100% 10%, ${mix(accent, 45 * strength, primary)} 0%, transparent 62%)`,
        `linear-gradient(150deg, ${primary} 0%, ${mix(accent, 25 * strength, primary)} 100%)`,
      ].join(", ");
  }
}

/**
 * Build the CSS value for a gradient surface.
 *
 * Args:
 *   surface: Which surface the gradient is applied to.
 *   variant: One of `gradientVariants`; `custom` returns `customValue` as is.
 *   customValue: Raw CSS `background-image` value for the custom variant.
 *
 * Returns:
 *   A CSS value, or `undefined` when the surface should stay flat.
 */
export function buildGradient(
  surface: GradientSurface,
  variant: GradientVariant,
  customValue?: string,
): string | undefined {
  if (variant === "custom") {
    const trimmed = customValue?.trim();
    return trimmed ? trimmed : undefined;
  }

  return surface === "brand"
    ? brandGradient(variant)
    : surfaceGradient(surface, variant);
}

/**
 * Find the variant a resolved gradient value corresponds to.
 *
 * Used by the picker to highlight the active option, including for gradients
 * that came from a preset rather than from the editor.
 */
export function matchGradientVariant(
  surface: GradientSurface,
  value?: string,
): GradientVariant {
  if (!value || value.trim() === "" || value.trim() === "none") return "none";

  const known = gradientVariants
    .filter((variant) => variant.value !== "none" && variant.value !== "custom")
    .map((variant) => variant.value);

  for (const variant of known) {
    if (buildGradient(surface, variant) === value.trim()) return variant;
  }

  return "custom";
}
