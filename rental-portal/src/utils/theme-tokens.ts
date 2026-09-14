/**
 * Token resolution helpers for the theme editor.
 *
 * A theme is always the selected preset's tokens layered with the user's
 * per-mode overrides. Keeping the three operations (resolve, diff, copy) here
 * means the React layer never has to reason about token merging.
 */

import type { ThemeMode } from "@/types/theme-customizer";
import {
  colorThemes,
  estateThemes,
  findColorTheme,
  tweakcnThemes,
} from "@/config/theme-data";
import { editableTokens, gradientTokens } from "@/config/theme-token-groups";
import type { SavedThemeState } from "@/utils/theme-storage";

type Tokens = Record<string, string>;

/** Token names copied when mirroring one mode onto the other. */
export const mirroredThemeTokens: string[] = [
  ...editableTokens,
  ...Object.values(gradientTokens),
];

/** Preset (or imported theme) tokens for a mode, before overrides. */
export function baseThemeTokens(
  state: SavedThemeState,
  mode: ThemeMode,
): Tokens {
  if (state.family === "imported") {
    return state.importedTheme?.[mode] ?? {};
  }
  if (!state.preset) return {};

  const preset = findColorTheme(state.preset)?.preset;
  const styles = mode === "dark" ? preset?.styles.dark : preset?.styles.light;
  return styles ?? {};
}

/** Overrides stored for a mode. */
export function storedOverrides(
  state: SavedThemeState,
  mode: ThemeMode,
): Tokens {
  return state.overrides[mode] ?? {};
}

/**
 * Make sure a loaded preset key and its preset family agree.
 *
 * Keeps records written by earlier versions (or by a preset that has since been
 * removed) consistent with the preset lists the customizer offers.
 */
export function resolveFamily(state: SavedThemeState): SavedThemeState {
  if (state.family === "imported" || !state.preset) return state;

  const families = [
    { family: "estate" as const, themes: estateThemes },
    { family: "shadcn" as const, themes: colorThemes },
    { family: "tweakcn" as const, themes: tweakcnThemes },
  ];

  for (const candidate of families) {
    if (candidate.themes.some((theme) => theme.value === state.preset)) {
      return { ...state, family: candidate.family };
    }
  }

  return state;
}

/**
 * Layer overrides on top of a preset's tokens.
 *
 * Args:
 *   base: Tokens from the selected preset (or an imported theme).
 *   overrides: Tokens the user tuned for this mode.
 *
 * Returns:
 *   The tokens to write to the document. Blank override values are ignored so
 *   an empty input falls back to the preset instead of clearing the token.
 */
export function resolveThemeTokens(
  base: Tokens | undefined,
  overrides: Tokens | undefined,
): Tokens {
  const resolved: Tokens = { ...(base ?? {}) };

  for (const [token, value] of Object.entries(overrides ?? {})) {
    if (typeof value === "string" && value.trim() !== "") {
      resolved[token] = value;
    }
  }

  return resolved;
}

/**
 * Keep only the overrides that actually differ from the preset, so switching
 * presets is not blocked by stale copies of the previous preset's colours.
 */
export function diffThemeTokens(
  base: Tokens | undefined,
  resolved: Tokens,
): Tokens {
  const overrides: Tokens = {};

  for (const [token, value] of Object.entries(resolved)) {
    if (value.trim() === "") continue;
    if (base?.[token] === value) continue;
    overrides[token] = value;
  }

  return overrides;
}

/**
 * Copy the given tokens from one mode to the other.
 *
 * Args:
 *   source: Resolved tokens of the mode being copied from.
 *   tokens: Token names to copy.
 *
 * Returns:
 *   The copied values, ready to be stored as overrides for the other mode.
 */
export function pickThemeTokens(source: Tokens, tokens: string[]): Tokens {
  const picked: Tokens = {};

  for (const token of tokens) {
    const value = source[token];
    if (value && value.trim() !== "") picked[token] = value;
  }

  return picked;
}

/** Human readable label for a mode, used by the editor controls. */
export function modeLabel(mode: ThemeMode): string {
  return mode === "dark" ? "Dark" : "Light";
}
