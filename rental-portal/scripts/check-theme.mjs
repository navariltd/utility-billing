/**
 * Theme engine checks.
 *
 * Bundles the theme engine with the project's own bundler (rolldown, the same
 * one Vite uses) and asserts the invariants the customizer relies on:
 *
 *   1. every built-in preset defines every editable token in both modes;
 *   2. preset metadata and the authored colours of the default preset;
 *   3. gradient builders produce usable CSS and round-trip through matching;
 *   4. token merging (resolve / diff / copy) behaves as documented.
 *
 * Run with `yarn check:theme`. It needs no extra dependencies and only writes
 * inside `node_modules/.tmp`.
 */

import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = path.resolve(import.meta.dirname, "..");
const workDir = path.join(root, "node_modules", ".tmp", "theme-check");
const entryFile = path.join(workDir, "entry.ts");
const configFile = path.join(workDir, "rolldown.config.mjs");
const bundleFile = path.join(workDir, "engine.mjs");

const ENTRY = `
export { estateThemePresets, DEFAULT_ESTATE_THEME } from "@/utils/estate-presets";
export {
  buildGradient,
  gradientVariants,
  matchGradientVariant,
} from "@/utils/theme-gradients";
export { diffThemeTokens, pickThemeTokens, resolveThemeTokens } from "@/utils/theme-tokens";
export { editableTokens, gradientTokens, presetTokens, themeTokenGroups } from "@/config/theme-token-groups";
`;

const CONFIG = `
import path from "node:path";

export default {
  input: ${JSON.stringify(entryFile)},
  output: { file: ${JSON.stringify(bundleFile)}, format: "esm" },
  resolve: { alias: { "@": path.join(${JSON.stringify(root)}, "src") } },
  platform: "neutral",
};
`;

function bundle() {
  mkdirSync(workDir, { recursive: true });
  writeFileSync(entryFile, ENTRY);
  writeFileSync(configFile, CONFIG);

  const bin = path.join(
    root,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "rolldown.cmd" : "rolldown",
  );

  execFileSync(bin, ["-c", configFile], { cwd: root, stdio: "pipe" });
}

const failures = [];
const notes = [];

function check(condition, message) {
  if (!condition) failures.push(message);
}

function equal(actual, expected, label) {
  check(
    actual === expected,
    `${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
  );
}

bundle();

const engine = await import(pathToFileURL(bundleFile).href);
const {
  DEFAULT_ESTATE_THEME,
  buildGradient,
  diffThemeTokens,
  editableTokens,
  estateThemePresets,
  gradientTokens,
  gradientVariants,
  matchGradientVariant,
  pickThemeTokens,
  presetTokens,
  resolveThemeTokens,
  themeTokenGroups,
} = engine;

/* ---------------------------------------------------------------- presets -- */

const REQUIRED_TOKENS = [
  ...presetTokens,
  "radius",
  "font-sans",
  "font-serif",
  "font-mono",
];

const presetKeys = Object.keys(estateThemePresets);
const EXPECTED_PRESETS = 16;

check(
  presetKeys.length === EXPECTED_PRESETS,
  `expected ${EXPECTED_PRESETS} presets, found ${presetKeys.length}`,
);
equal(presetKeys[0], DEFAULT_ESTATE_THEME, "default preset is listed first");

const recommended = presetKeys.filter(
  (key) => estateThemePresets[key].recommended,
);
equal(recommended.join(","), DEFAULT_ESTATE_THEME, "only the default is recommended");

const labels = presetKeys.map((key) => estateThemePresets[key].label);
check(new Set(labels).size === labels.length, `duplicate preset labels: ${labels}`);

for (const mode of ["light", "dark"]) {
  const primaries = presetKeys.map(
    (key) => estateThemePresets[key].styles[mode].primary,
  );
  check(
    new Set(primaries).size === primaries.length,
    `${mode}: two presets share a primary colour`,
  );
}

for (const [key, preset] of Object.entries(estateThemePresets)) {
  check(Boolean(preset.label), `${key}: missing label`);
  check(Boolean(preset.description), `${key}: missing description`);
  equal(preset.source, "BUILT_IN", `${key}: preset source`);

  for (const mode of ["light", "dark"]) {
    const styles = preset.styles[mode];
    const missing = REQUIRED_TOKENS.filter((token) => !styles[token]);
    check(missing.length === 0, `${key}/${mode}: missing ${missing.join(", ")}`);
    check(
      Object.values(styles).every(
        (value) => typeof value === "string" && value.trim() !== "",
      ),
      `${key}/${mode}: contains an empty value`,
    );
  }

  // Presets ship flat: gradients are opt in from the theme editor.
  for (const token of Object.values(gradientTokens)) {
    equal(preset.styles.light[token], undefined, `${key}/light: ${token} must not be preset`);
    equal(preset.styles.dark[token], undefined, `${key}/dark: ${token} must not be preset`);
  }
}

/* --------------------------------------------------- authored default spec -- */

const navy = estateThemePresets[DEFAULT_ESTATE_THEME];
const expectations = [
  [navy.styles.light.primary, "#0f2747", "Estate Navy light primary"],
  [navy.styles.light.accent, "#c9a227", "Estate Navy light accent"],
  [navy.styles.light.radius, "0.5rem", "Estate Navy light radius"],
  [navy.styles.light.sidebar, "#f7f9fc", "Estate Navy light sidebar"],
  [navy.styles.dark.primary, "#3b82f6", "Estate Navy dark primary"],
  [navy.styles.dark.accent, "#d4af37", "Estate Navy dark accent"],
  [navy.styles.dark.sidebar, "#0e1622", "Estate Navy dark sidebar"],
  [estateThemePresets["obsidian-gold"].styles.dark.radius, "0.3rem", "Obsidian radius"],
  [estateThemePresets["modern-graphite"].styles.light.radius, "0.75rem", "Graphite radius"],
  [estateThemePresets["midnight-aurora"].styles.dark.accent, "#22d3ee", "Aurora accent"],
];

for (const [actual, expected, label] of expectations) {
  equal(actual, expected, label);
}

/* --------------------------------------------------------------- gradients -- */

const surfaces = Object.keys(gradientTokens);

for (const surface of surfaces) {
  for (const variant of gradientVariants.map((entry) => entry.value)) {
    const value = buildGradient(surface, variant);

    if (variant === "none") {
      equal(value, undefined, `${surface}/none builds nothing`);
      equal(matchGradientVariant(surface, "none"), "none", `${surface}/none match`);
      continue;
    }

    if (variant === "custom") {
      equal(
        buildGradient(surface, variant, "   "),
        undefined,
        `${surface}/custom ignores whitespace`,
      );
      const custom = "linear-gradient(90deg, #000, #fff)";
      equal(buildGradient(surface, variant, custom), custom, `${surface}/custom passthrough`);
      equal(matchGradientVariant(surface, custom), "custom", `${surface}/custom match`);
      continue;
    }

    check(
      typeof value === "string" && value.length > 0,
      `${surface}/${variant} produced no gradient`,
    );
    check(
      typeof value === "string" && /gradient\(/.test(value) && /var\(--|color-mix\(/.test(value),
      `${surface}/${variant} should reference theme tokens`,
    );
    equal(matchGradientVariant(surface, value), variant, `${surface}/${variant} round trip`);
  }

  equal(matchGradientVariant(surface, undefined), "none", `${surface}: unset is none`);
  equal(matchGradientVariant(surface, ""), "none", `${surface}: empty is none`);
}

/* ------------------------------------------------------------ token merging -- */

const base = { primary: "#000", muted: "#eee" };
const merged = resolveThemeTokens(base, {
  primary: "#fff",
  accent: "   ",
  extra: "#123",
});
equal(merged.primary, "#fff", "resolve: override wins");
equal(merged.muted, "#eee", "resolve: preset token kept");
equal(merged.accent, undefined, "resolve: blank override ignored");
equal(merged.extra, "#123", "resolve: new token added");
equal(
  Object.keys(resolveThemeTokens(undefined, undefined)).length,
  0,
  "resolve: empty inputs are safe",
);

const diffed = diffThemeTokens(base, { ...base, primary: "#fff", accent: "" });
equal(Object.keys(diffed).join(","), "primary", "diff keeps only real changes");

const copied = pickThemeTokens(
  { primary: "#111", accent: "", "background-gradient": "g" },
  ["primary", "accent", "background-gradient"],
);
equal(
  Object.keys(copied).join(","),
  "primary,background-gradient",
  "copy skips blanks",
);

/* --------------------------------------------------------------- catalogue -- */

const catalogueTokens = themeTokenGroups.flatMap((group) =>
  group.tokens.map((token) => token.token),
);
const duplicates = catalogueTokens.filter(
  (token, index) => catalogueTokens.indexOf(token) !== index,
);
check(duplicates.length === 0, `catalogue has duplicate tokens: ${duplicates}`);
equal(editableTokens.length, catalogueTokens.length, "editableTokens covers the catalogue");

const coveredSurfaces = new Set(
  themeTokenGroups.flatMap((group) => group.gradients ?? []),
);
for (const surface of surfaces) {
  check(coveredSurfaces.has(surface), `gradient surface ${surface} is not editable`);
}

for (const token of catalogueTokens) {
  if (!navy.styles.light[token] && !navy.styles.dark[token]) {
    notes.push(`${token} is not set by the default preset (falls back to index.css)`);
  }
}

/* ------------------------------------------------------------------ report -- */

rmSync(workDir, { recursive: true, force: true });

console.log(`presets (${presetKeys.length}): ${presetKeys.join(", ")}`);
console.log(`editable tokens: ${editableTokens.length}, gradient surfaces: ${surfaces.join(", ")}`);
for (const note of [...new Set(notes)]) console.log(`note: ${note}`);

if (failures.length > 0) {
  console.error(`\nFAIL (${failures.length})\n - ${failures.join("\n - ")}`);
  process.exit(1);
}

console.log("\nPASS: theme engine checks passed");
