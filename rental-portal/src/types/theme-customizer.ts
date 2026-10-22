export interface ThemePreset {
  label?: string
  styles: {
    light: Record<string, string>
    dark: Record<string, string>
  }
}

/** The two modes a theme can be edited for. */
export type ThemeMode = "light" | "dark"

/**
 * Per-mode token overrides.
 *
 * Values are raw CSS declarations keyed by token name (`primary`, `sidebar`,
 * `background-gradient`, ...). They are layered on top of the selected preset
 * and written to the document as `--<token>`, so a tuned colour always survives
 * a preset change, a mode switch and a page reload.
 */
export type ModeOverrides = Record<ThemeMode, Record<string, string>>

/** A single editable design token. */
export interface ThemeToken {
  name: string
  /** Token key without the leading `--`, e.g. `sidebar-accent`. */
  token: string
  /** Example value shown in the empty input. */
  hint?: string
  /**
   * Tokens a preset does not have to define. The editor falls back to the
   * computed value from `index.css` for these (semantic state colours), so they
   * are editable without every preset having to repeat them.
   */
  optional?: boolean
}

/** A collapsible group of editable tokens. */
export interface ThemeTokenGroup {
  id: string
  label: string
  description: string
  tokens: ThemeToken[]
  /** Gradient surfaces edited inside this group. */
  gradients?: GradientSurface[]
}

/** Surfaces a gradient can be applied to. */
export type GradientSurface = "page" | "sidebar" | "brand"

export interface ColorTheme {
  name: string
  value: string
  preset: ThemePreset
  /** Short description shown by the preset picker. */
  description?: string
  /** Marks the preset the portal ships with by default. */
  recommended?: boolean
}

export interface SidebarVariant {
  name: string
  value: "sidebar" | "floating" | "inset"
  description: string
}

export interface SidebarCollapsibleOption {
  name: string
  value: "offcanvas" | "icon" | "none"
  description: string
}

export interface SidebarSideOption {
  name: string
  value: "left" | "right"
}

export interface RadiusOption {
  name: string
  value: string
}

export interface ImportedTheme {
  light: Record<string, string>
  dark: Record<string, string>
}
