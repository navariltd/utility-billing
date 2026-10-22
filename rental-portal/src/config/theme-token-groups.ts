/**
 * Catalogue of every design token the theme editor exposes.
 *
 * The editor, the preset previews and the override store all iterate over this
 * list, so adding a token to the customizer is a one line change here (the CSS
 * variable must also be mapped in `src/index.css` under `@theme inline`).
 */

import type { ThemeTokenGroup } from "@/types/theme-customizer";

export const themeTokenGroups: ThemeTokenGroup[] = [
  {
    id: "brand",
    label: "Brand",
    description: "Buttons, links, highlights and focus rings",
    gradients: ["brand"],
    tokens: [
      { name: "Primary", token: "primary", hint: "#0f2747" },
      { name: "Primary Foreground", token: "primary-foreground", hint: "#ffffff" },
      { name: "Secondary", token: "secondary", hint: "#e8eef5" },
      { name: "Secondary Foreground", token: "secondary-foreground", hint: "#0f2747" },
      { name: "Accent", token: "accent", hint: "#c9a227" },
      { name: "Accent Foreground", token: "accent-foreground", hint: "#ffffff" },
      { name: "Ring", token: "ring", hint: "#c9a227" },
    ],
  },
  {
    id: "surfaces",
    label: "Background & Surfaces",
    description: "Page, cards, popovers and borders",
    gradients: ["page"],
    tokens: [
      { name: "Background", token: "background", hint: "#f7f9fc" },
      { name: "Foreground", token: "foreground", hint: "#0f172a" },
      { name: "Card", token: "card", hint: "#ffffff" },
      { name: "Card Foreground", token: "card-foreground", hint: "#0f172a" },
      { name: "Popover", token: "popover", hint: "#ffffff" },
      { name: "Popover Foreground", token: "popover-foreground", hint: "#0f172a" },
      { name: "Muted", token: "muted", hint: "#f1f5f9" },
      { name: "Muted Foreground", token: "muted-foreground", hint: "#64748b" },
      { name: "Border", token: "border", hint: "#e2e8f0" },
      { name: "Input", token: "input", hint: "#e2e8f0" },
    ],
  },
  {
    id: "sidebar",
    label: "Sidebar",
    description: "Navigation surface, active item and border",
    gradients: ["sidebar"],
    tokens: [
      { name: "Sidebar", token: "sidebar", hint: "#f7f9fc" },
      { name: "Sidebar Foreground", token: "sidebar-foreground", hint: "#0f2747" },
      { name: "Sidebar Accent", token: "sidebar-accent", hint: "#e8eef5" },
      { name: "Sidebar Accent Foreground", token: "sidebar-accent-foreground", hint: "#0f2747" },
      { name: "Sidebar Border", token: "sidebar-border", hint: "#e2e8f0" },
      { name: "Sidebar Primary", token: "sidebar-primary", hint: "#0f2747" },
      { name: "Sidebar Primary Foreground", token: "sidebar-primary-foreground", hint: "#ffffff" },
      { name: "Sidebar Ring", token: "sidebar-ring", hint: "#c9a227" },
    ],
  },
  {
    id: "states",
    label: "States & Feedback",
    description: "Success, warning, info and destructive",
    tokens: [
      { name: "Success", token: "success", hint: "oklch(0.627 0.194 149.214)", optional: true },
      { name: "Success Foreground", token: "success-foreground", hint: "#f0fdf4", optional: true },
      { name: "Warning", token: "warning", hint: "oklch(0.705 0.155 71.249)", optional: true },
      { name: "Warning Foreground", token: "warning-foreground", hint: "#fffbeb", optional: true },
      { name: "Info", token: "info", hint: "oklch(0.546 0.245 262.881)", optional: true },
      { name: "Info Foreground", token: "info-foreground", hint: "#eff6ff", optional: true },
      { name: "Destructive", token: "destructive", hint: "#dc2626" },
      { name: "Destructive Foreground", token: "destructive-foreground", hint: "#ffffff" },
    ],
  },
  {
    id: "data",
    label: "Charts",
    description: "Series colours used by the report charts",
    tokens: [
      { name: "Chart 1", token: "chart-1", hint: "#0f2747" },
      { name: "Chart 2", token: "chart-2", hint: "#c9a227" },
      { name: "Chart 3", token: "chart-3", hint: "#3b82f6" },
      { name: "Chart 4", token: "chart-4", hint: "#0d9488" },
      { name: "Chart 5", token: "chart-5", hint: "#475569" },
    ],
  },
];

/** Groups expanded when the theme editor opens. */
export const defaultOpenTokenGroups = ["brand", "surfaces", "sidebar"];

/** Every token name the editor can write, used when copying between modes. */
export const editableTokens: string[] = themeTokenGroups.flatMap((group) =>
  group.tokens.map((token) => token.token),
);

/**
 * Tokens every preset must define. The optional tokens (semantic state
 * colours) may fall back to `index.css`.
 */
export const presetTokens: string[] = themeTokenGroups.flatMap((group) =>
  group.tokens.filter((token) => !token.optional).map((token) => token.token),
);

/** Gradient token written per surface. */
export const gradientTokens: Record<string, string> = {
  page: "background-gradient",
  sidebar: "sidebar-gradient",
  brand: "primary-gradient",
};
