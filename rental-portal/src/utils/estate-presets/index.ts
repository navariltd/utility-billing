/**
 * Built-in property-management theme presets.
 *
 * These are the presets the portal ships with and the ones shown first in the
 * theme customizer. `DEFAULT_ESTATE_THEME` is applied on first visit.
 */

import type { ThemePreset } from "../../types/theme";
import { arcticMint } from "./arctic-mint";
import { azureProperty } from "./azure-property";
import { burgundyReserve } from "./burgundy-reserve";
import { cyberLime } from "./cyber-lime";
import { emeraldEstate } from "./emerald-estate";
import { estateNavy } from "./estate-navy";
import { indigoEstate } from "./indigo-estate";
import { midnightAurora } from "./midnight-aurora";
import { mochaEstate } from "./mocha-estate";
import { modernGraphite } from "./modern-graphite";
import { nairobiSlate } from "./nairobi-slate";
import { obsidianGold } from "./obsidian-gold";
import { oceanic } from "./oceanic";
import { roseQuartz } from "./rose-quartz";
import { steelBlueprint } from "./steel-blueprint";
import { terracottaEstate } from "./terracotta-estate";

/** Preset applied when a visitor has never chosen a theme. */
export const DEFAULT_ESTATE_THEME = "estate-navy";

/**
 * Presets in the order they are presented in the customizer.
 *
 * Property and enterprise palettes come first, then the contemporary ones.
 * Every preset is flat: gradients are applied by the user in the theme editor.
 */
export const estateThemePresets: Record<string, ThemePreset> = {
  "estate-navy": estateNavy,
  "nairobi-slate": nairobiSlate,
  "emerald-estate": emeraldEstate,
  "obsidian-gold": obsidianGold,
  "azure-property": azureProperty,
  "indigo-estate": indigoEstate,
  "terracotta-estate": terracottaEstate,
  "modern-graphite": modernGraphite,
  "steel-blueprint": steelBlueprint,
  "mocha-estate": mochaEstate,
  "burgundy-reserve": burgundyReserve,
  "arctic-mint": arcticMint,
  oceanic: oceanic,
  "midnight-aurora": midnightAurora,
  "rose-quartz": roseQuartz,
  "cyber-lime": cyberLime,
};

export {
  arcticMint,
  azureProperty,
  burgundyReserve,
  cyberLime,
  emeraldEstate,
  estateNavy,
  indigoEstate,
  midnightAurora,
  mochaEstate,
  modernGraphite,
  nairobiSlate,
  obsidianGold,
  oceanic,
  roseQuartz,
  steelBlueprint,
  terracottaEstate,
};
