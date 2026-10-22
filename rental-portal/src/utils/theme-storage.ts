/**
 * Persistence for the theme editor.
 *
 * The saved record holds the selected preset family/key, the radius, the
 * per-mode token overrides and any imported theme. Records written by earlier
 * versions of the customizer (three separate preset keys, no overrides) are
 * migrated on load so existing users keep their theme.
 */

import type { ImportedTheme, ModeOverrides } from "@/types/theme-customizer";
import { DEFAULT_ESTATE_THEME } from "@/utils/estate-presets";

const STORAGE_KEY = "rental-portal:theme";

/** Which preset list the selected key belongs to. */
export type ThemeFamily = "estate" | "shadcn" | "tweakcn" | "imported";

export interface SavedThemeState {
  /** Preset family in use, empty when the app defaults should apply. */
  family: ThemeFamily | "";
  /** Preset key inside the family (empty for imported themes). */
  preset: string;
  radius: string;
  overrides: ModeOverrides;
  importedTheme: ImportedTheme | null;
}

/** Theme applied to a visitor who has never used the customizer. */
export const defaultThemeState: SavedThemeState = {
  family: "estate",
  preset: DEFAULT_ESTATE_THEME,
  radius: "0.5rem",
  overrides: { light: {}, dark: {} },
  importedTheme: null,
};

const EMPTY_OVERRIDES: ModeOverrides = { light: {}, dark: {} };

/** Ensure both modes exist and only string values are kept. */
function normalizeOverrides(raw: unknown): ModeOverrides {
  if (!raw || typeof raw !== "object") return { ...EMPTY_OVERRIDES };

  const source = raw as Record<string, unknown>;
  const normalize = (mode: unknown): Record<string, string> => {
    if (!mode || typeof mode !== "object") return {};
    const entries = Object.entries(mode as Record<string, unknown>).filter(
      ([, value]) => typeof value === "string",
    ) as [string, string][];
    return Object.fromEntries(entries);
  };

  return { light: normalize(source.light), dark: normalize(source.dark) };
}

/** Read the persisted state, migrating the legacy shape when needed. */
export function loadSavedTheme(): SavedThemeState | null {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (!parsed || typeof parsed !== "object") return null;

    // Legacy record: three preset keys and no overrides/family.
    if (!("family" in parsed) && !("overrides" in parsed)) {
      const imported = (parsed.importedTheme ?? null) as ImportedTheme | null;
      const legacyPreset =
        (parsed.selectedEstateTheme as string) ||
        (parsed.selectedTheme as string) ||
        (parsed.selectedTweakcnTheme as string) ||
        "";

      return {
        family: imported ? "imported" : "",
        preset: imported ? "" : legacyPreset,
        radius: (parsed.selectedRadius as string) || defaultThemeState.radius,
        overrides: { light: {}, dark: {} },
        importedTheme: imported,
      };
    }

    return {
      family: (parsed.family as SavedThemeState["family"]) ?? "",
      preset: (parsed.preset as string) ?? "",
      radius: (parsed.radius as string) || defaultThemeState.radius,
      overrides: normalizeOverrides(parsed.overrides),
      importedTheme: (parsed.importedTheme ?? null) as ImportedTheme | null,
    };
  } catch {
    return null;
  }
}

/** Persist the theme state; storage failures never break the UI. */
export function saveThemeState(state: SavedThemeState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore quota / private mode failures.
  }
}
