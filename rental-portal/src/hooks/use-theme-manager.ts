/**
 * Low level DOM applier for the theme editor.
 *
 * This hook only knows how to write tokens onto the document; resolving which
 * tokens to write (preset + overrides, per mode) is the job of
 * `ThemeEditorProvider`. Everything is written as inline CSS variables so a
 * theme override never needs a rebuild.
 */

"use client";

import * as React from "react";
import { findColorTheme } from "@/config/theme-data";
import { useTheme } from "@/hooks/use-theme";

export function useThemeManager() {
  const { theme, setTheme } = useTheme();

  const isDarkMode = React.useMemo(() => {
    if (theme === "dark") return true;
    if (theme === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }, [theme]);

  /** Switch the app between light and dark. */
  const setDarkMode = React.useCallback(
    (dark: boolean) => setTheme(dark ? "dark" : "light"),
    [setTheme],
  );

  /** Remove every theme token written inline (back to the `index.css` values). */
  const clearStyles = React.useCallback(() => {
    const inline = document.documentElement.style;
    for (let index = inline.length - 1; index >= 0; index -= 1) {
      if (inline[index].startsWith("--")) {
        document.documentElement.style.removeProperty(inline[index]);
      }
    }
  }, []);

  /**
   * Write a full token set onto the document.
   *
   * Args:
   *   styles: Token name (without the leading `--`) to CSS value, already
   *     resolved for the active mode.
   */
  const applyStyles = React.useCallback(
    (styles: Record<string, string>) => {
      clearStyles();
      const root = document.documentElement;

      Object.entries(styles).forEach(([token, value]) => {
        if (typeof value === "string" && value.trim() !== "") {
          root.style.setProperty(`--${token}`, value);
        }
      });
    },
    [clearStyles],
  );

  /** Override the radius without touching the rest of the theme. */
  const applyRadius = React.useCallback((radius: string) => {
    document.documentElement.style.setProperty("--radius", radius);
  }, []);

  /**
   * Radius declared by a preset, used to keep the radius picker in sync with
   * the preset that was applied.
   *
   * Args:
   *   themeValue: Preset key from `allColorThemes`.
   *   darkMode: Which variant of the preset to read.
   */
  const getPresetRadius = React.useCallback(
    (themeValue: string, darkMode: boolean) => {
      const preset = findColorTheme(themeValue)?.preset;
      if (!preset) return undefined;
      const styles = darkMode ? preset.styles.dark : preset.styles.light;
      return styles.radius;
    },
    [],
  );

  return {
    theme,
    isDarkMode,
    setDarkMode,
    clearStyles,
    applyStyles,
    applyRadius,
    getPresetRadius,
  };
}
