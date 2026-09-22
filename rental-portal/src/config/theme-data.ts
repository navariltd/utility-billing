import { estateThemePresets } from '@/utils/estate-presets'
import { shadcnThemePresets } from '@/utils/shadcn-ui-theme-presets'
import { tweakcnPresets } from '@/utils/tweakcn-theme-presets'
import type { ColorTheme } from '@/types/theme-customizer'

// Tweakcn theme presets for the dropdown - convert from tweakcnPresets
export const tweakcnThemes: ColorTheme[] = Object.entries(tweakcnPresets).map(([key, preset]) => ({
  name: preset.label || key,
  value: key,
  preset: preset
}))

// Shadcn theme presets for the dropdown - convert from shadcnThemePresets  
export const colorThemes: ColorTheme[] = Object.entries(shadcnThemePresets).map(([key, preset]) => ({
  name: preset.label || key,
  value: key,
  preset: preset
}))

// Built-in property management presets - shown first in the theme customizer
export const estateThemes: ColorTheme[] = Object.entries(estateThemePresets).map(([key, preset]) => ({
  name: preset.label || key,
  value: key,
  preset: preset,
  description: preset.description,
  recommended: preset.recommended
}))

/**
 * Every preset the customizer can apply, keyed by its value.
 *
 * The theme editor resolves a selected preset against this list, so a built-in
 * property preset is applied exactly like a shadcn or Tweakcn one.
 */
export const allColorThemes: ColorTheme[] = [...estateThemes, ...colorThemes, ...tweakcnThemes]

/** Look up a preset by its value across every known preset source. */
export function findColorTheme(value: string): ColorTheme | undefined {
  return allColorThemes.find((theme) => theme.value === value)
}

