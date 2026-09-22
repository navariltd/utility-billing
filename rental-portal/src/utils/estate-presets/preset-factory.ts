/**
 * Factory for the built-in property-management theme presets.
 *
 * A preset is authored as the design tokens that the shadcn/Tailwind theme
 * exposes, once per mode (light/dark). The factory keeps the authoring surface
 * small by filling in the tokens that are identical across every preset
 * (destructive colours and font stacks) and by defaulting the radius, so each
 * preset file only spells out the colours that make it distinctive.
 */

import type { ThemePreset, ThemeStyleProps } from "../../types/theme";

/**
 * The tokens a preset must define for one mode.
 *
 * The remaining shadcn tokens (`destructive`, fonts) are supplied by the
 * factory; semantic state colours (`success`, `warning`, `info`) live in
 * `index.css` because they are identical for every theme.
 */
export type EstateModeTokens = Pick<
  ThemeStyleProps,
  | "background"
  | "foreground"
  | "card"
  | "card-foreground"
  | "popover"
  | "popover-foreground"
  | "primary"
  | "primary-foreground"
  | "secondary"
  | "secondary-foreground"
  | "muted"
  | "muted-foreground"
  | "accent"
  | "accent-foreground"
  | "border"
  | "input"
  | "ring"
  | "chart-1"
  | "chart-2"
  | "chart-3"
  | "chart-4"
  | "chart-5"
  | "sidebar"
  | "sidebar-foreground"
  | "sidebar-primary"
  | "sidebar-primary-foreground"
  | "sidebar-accent"
  | "sidebar-accent-foreground"
  | "sidebar-border"
  | "sidebar-ring"
> & {
  /** Overrides `DEFAULT_ESTATE_RADIUS` for the preset. */
  radius?: string;
};

/** Authoring shape of a built-in preset. */
export interface EstatePresetSpec {
  label: string;
  /** One line shown under the preset name in the theme customizer. */
  description: string;
  /** Marks the preset the portal ships with by default. */
  recommended?: boolean;
  light: EstateModeTokens;
  dark: EstateModeTokens;
}

/** Radius used when a preset does not ask for a different one. */
export const DEFAULT_ESTATE_RADIUS = "0.5rem";

/** Font stacks shared by every preset. */
const estateFonts = {
  "font-sans": "Inter, ui-sans-serif, system-ui, sans-serif",
  "font-serif": "Source Serif 4, Georgia, serif",
  "font-mono": "JetBrains Mono, ui-monospace, SFMono-Regular, monospace",
} satisfies Partial<ThemeStyleProps>;

/** Feedback colours shared by every preset, tuned per mode for contrast. */
const sharedTokens: Record<"light" | "dark", Partial<ThemeStyleProps>> = {
  light: {
    destructive: "#dc2626",
    "destructive-foreground": "#ffffff",
  },
  dark: {
    destructive: "#f87171",
    "destructive-foreground": "#450a0a",
  },
};

/**
 * Build one mode of a preset by merging the shared tokens into the authored
 * ones (authored values win so a preset can override anything).
 */
function buildMode(
  tokens: EstateModeTokens,
  mode: "light" | "dark",
): Partial<ThemeStyleProps> {
  return {
    ...sharedTokens[mode],
    ...estateFonts,
    radius: DEFAULT_ESTATE_RADIUS,
    ...tokens,
  };
}

/**
 * Create a complete built-in theme preset.
 *
 * Presets ship flat: gradients are deliberately not part of a preset, they are
 * applied by the user from the theme editor and stored as per-mode overrides.
 *
 * Args:
 *   spec: The authored light and dark token sets plus display metadata.
 *
 * Returns:
 *   A `ThemePreset` ready to be applied by the theme editor.
 */
export function createEstatePreset(spec: EstatePresetSpec): ThemePreset {
  return {
    source: "BUILT_IN",
    label: spec.label,
    description: spec.description,
    recommended: spec.recommended,
    styles: {
      light: buildMode(spec.light, "light"),
      dark: buildMode(spec.dark, "dark"),
    },
  };
}
