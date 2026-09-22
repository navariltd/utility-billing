"use client";

/**
 * Portal theme editor.
 *
 * Owns the whole theming model in one place: the selected preset, the radius,
 * imported themes and the per-mode token overrides, and applies the resolved
 * tokens to the document. It is mounted above the router so every page (portal
 * shell, auth pages, error pages) is themed, and so the customizer, the preset
 * previews and the colour editors all read the same state.
 */

import * as React from "react";
import { gradientTokens } from "@/config/theme-token-groups";
import { colorThemes, estateThemes, tweakcnThemes } from "@/config/theme-data";
import { useThemeManager } from "@/hooks/use-theme-manager";
import type {
  ColorTheme,
  GradientSurface,
  ImportedTheme,
  ModeOverrides,
  ThemeMode,
} from "@/types/theme-customizer";
import {
  defaultThemeState,
  loadSavedTheme,
  saveThemeState,
  type SavedThemeState,
  type ThemeFamily,
} from "@/utils/theme-storage";
import {
  baseThemeTokens,
  diffThemeTokens,
  mirroredThemeTokens,
  pickThemeTokens,
  resolveFamily,
  resolveThemeTokens,
  storedOverrides,
} from "@/utils/theme-tokens";

interface ThemeEditorContextValue {
  isDarkMode: boolean;
  setDarkMode: (dark: boolean) => void;
  /** Mode the colour editors write to. */
  editMode: ThemeMode;
  setEditMode: (mode: ThemeMode) => void;
  family: ThemeFamily | "";
  preset: string;
  radius: string;
  importedTheme: ImportedTheme | null;
  estatePresets: ColorTheme[];
  shadcnPresets: ColorTheme[];
  tweakcnPresets: ColorTheme[];
  /** Resolved tokens for a mode: preset first, overrides on top. */
  tokens: (mode: ThemeMode) => Record<string, string>;
  overrides: ModeOverrides;
  hasOverrides: boolean;
  applyPreset: (family: ThemeFamily, value: string) => void;
  clearPreset: () => void;
  setRadius: (radius: string) => void;
  importTheme: (theme: ImportedTheme) => void;
  /** Set (or clear, with an empty value) a single token for a mode. */
  setToken: (mode: ThemeMode, token: string, value: string) => void;
  setTokens: (mode: ThemeMode, values: Record<string, string>) => void;
  /**
   * Set a surface gradient. Gradients are built from the theme's own tokens, so
   * the value is written to both modes and blends correctly in each.
   */
  setGradient: (surface: GradientSurface, value: string) => void;
  /** Copy the resolved tokens of one mode onto the other. */
  copyModeToOther: (mode: ThemeMode) => void;
  resetMode: (mode: ThemeMode) => void;
  resetTheme: () => void;
}

const ThemeEditorContext = React.createContext<ThemeEditorContextValue | null>(
  null,
);

export function ThemeEditorProvider({ children }: { children: React.ReactNode }) {
  const { isDarkMode, setDarkMode, applyStyles, applyRadius, getPresetRadius } =
    useThemeManager();

  const [state, setState] = React.useState<SavedThemeState>(defaultThemeState);
  const [editMode, setEditMode] = React.useState<ThemeMode>("light");
  const [hydrated, setHydrated] = React.useState(false);

  // Restore the saved theme; a first time visitor gets the default preset.
  React.useEffect(() => {
    const saved = loadSavedTheme();
    if (saved) setState(resolveFamily(saved));
    setHydrated(true);
  }, []);

  // The editor follows the appearance, so tuning what you see is the default.
  React.useEffect(() => {
    setEditMode(isDarkMode ? "dark" : "light");
  }, [isDarkMode]);

  const tokens = React.useCallback(
    (mode: ThemeMode) =>
      resolveThemeTokens(baseThemeTokens(state, mode), storedOverrides(state, mode)),
    [state],
  );

  // Apply + persist whenever the selection, the overrides or the mode change.
  React.useEffect(() => {
    if (!hydrated) return;

    applyStyles(tokens(isDarkMode ? "dark" : "light"));
    applyRadius(state.radius);
    saveThemeState(state);
  }, [hydrated, isDarkMode, state, tokens, applyStyles, applyRadius]);

  const updateState = React.useCallback((patch: Partial<SavedThemeState>) => {
    setState((previous) => ({ ...previous, ...patch }));
  }, []);

  const setToken = React.useCallback(
    (mode: ThemeMode, token: string, value: string) => {
      setState((previous) => {
        const base = baseThemeTokens(previous, mode);
        const next = { ...storedOverrides(previous, mode) };
        const trimmed = value.trim();

        // A value equal to the preset (or an empty one) clears the override so
        // the preset keeps control of that token.
        if (trimmed === "" || base[token] === value) {
          delete next[token];
        } else {
          next[token] = value;
        }

        return {
          ...previous,
          overrides: { ...previous.overrides, [mode]: next },
        };
      });
    },
    [],
  );

  const setTokens = React.useCallback(
    (mode: ThemeMode, values: Record<string, string>) => {
      setState((previous) => {
        const base = baseThemeTokens(previous, mode);
        return {
          ...previous,
          overrides: {
            ...previous.overrides,
            [mode]: {
              ...storedOverrides(previous, mode),
              ...diffThemeTokens(base, values),
            },
          },
        };
      });
    },
    [],
  );

  const applyPreset = React.useCallback(
    (family: ThemeFamily, value: string) => {
      const radius = getPresetRadius(value, isDarkMode);

      setState((previous) => ({
        family,
        preset: value,
        radius: radius ?? previous.radius,
        // A preset is a complete theme: start from a clean slate.
        overrides: { light: {}, dark: {} },
        importedTheme: null,
      }));
    },
    [getPresetRadius, isDarkMode],
  );

  const clearPreset = React.useCallback(() => {
    setState((previous) => ({
      ...previous,
      family: "",
      preset: "",
      overrides: { light: {}, dark: {} },
      importedTheme: null,
    }));
  }, []);

  const importTheme = React.useCallback(
    (theme: ImportedTheme) => {
      // An imported theme may declare its own radius; keep the picker in sync.
      const mode = isDarkMode ? "dark" : "light";
      setState({
        family: "imported",
        preset: "",
        radius: theme[mode]?.radius ?? defaultThemeState.radius,
        overrides: { light: {}, dark: {} },
        importedTheme: theme,
      });
    },
    [isDarkMode],
  );

  const setGradient = React.useCallback(
    (surface: GradientSurface, value: string) => {
      const token = gradientTokens[surface];

      setState((previous) => ({
        ...previous,
        overrides: {
          light: { ...previous.overrides.light, [token]: value },
          dark: { ...previous.overrides.dark, [token]: value },
        },
      }));
    },
    [],
  );

  const copyModeToOther = React.useCallback((mode: ThemeMode) => {
    const other: ThemeMode = mode === "dark" ? "light" : "dark";

    setState((previous) => {
      const source = resolveThemeTokens(
        baseThemeTokens(previous, mode),
        storedOverrides(previous, mode),
      );
      const copied = pickThemeTokens(source, mirroredThemeTokens);
      const otherBase = baseThemeTokens(previous, other);

      return {
        ...previous,
        overrides: {
          ...previous.overrides,
          [other]: {
            ...storedOverrides(previous, other),
            ...diffThemeTokens(otherBase, copied),
          },
        },
      };
    });
  }, []);

  const resetMode = React.useCallback((mode: ThemeMode) => {
    setState((previous) => ({
      ...previous,
      overrides: { ...previous.overrides, [mode]: {} },
    }));
  }, []);

  const resetTheme = React.useCallback(() => {
    setState(defaultThemeState);
  }, []);

  const hasOverrides = React.useMemo(
    () =>
      Object.keys(state.overrides.light).length > 0 ||
      Object.keys(state.overrides.dark).length > 0,
    [state.overrides],
  );

  const value = React.useMemo<ThemeEditorContextValue>(
    () => ({
      isDarkMode,
      setDarkMode,
      editMode,
      setEditMode,
      family: state.family,
      preset: state.preset,
      radius: state.radius,
      importedTheme: state.importedTheme,
      estatePresets: estateThemes,
      shadcnPresets: colorThemes,
      tweakcnPresets: tweakcnThemes,
      tokens,
      overrides: state.overrides,
      hasOverrides,
      applyPreset,
      clearPreset,
      setRadius: (radius: string) => updateState({ radius }),
      importTheme,
      setToken,
      setTokens,
      setGradient,
      copyModeToOther,
      resetMode,
      resetTheme,
    }),
    [
      isDarkMode,
      setDarkMode,
      editMode,
      state,
      tokens,
      hasOverrides,
      applyPreset,
      clearPreset,
      updateState,
      importTheme,
      setToken,
      setTokens,
      setGradient,
      copyModeToOther,
      resetMode,
      resetTheme,
    ],
  );

  return (
    <ThemeEditorContext.Provider value={value}>
      {children}
    </ThemeEditorContext.Provider>
  );
}

export function useThemeEditor(): ThemeEditorContextValue {
  const context = React.useContext(ThemeEditorContext);
  if (!context) {
    throw new Error("useThemeEditor must be used within a ThemeEditorProvider");
  }
  return context;
}

