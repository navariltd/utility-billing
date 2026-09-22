/**
 * Colour helpers shared by the theme editor.
 */

/**
 * Normalise a CSS colour to `#rrggbb` when the browser can parse it.
 *
 * Used to seed the native colour input, which only accepts hex. `oklch()` and
 * other wide gamut values that the canvas cannot parse return `undefined`; the
 * editor still previews them correctly and keeps the text value authoritative.
 */
export function cssColorToHex(value?: string): string | undefined {
  const trimmed = value?.trim();
  if (!trimmed) return undefined;
  if (/^#[0-9a-f]{6}$/i.test(trimmed)) return trimmed;

  if (/^#[0-9a-f]{3}$/i.test(trimmed)) {
    const [, r, g, b] = trimmed;
    return `#${r}${r}${g}${g}${b}${b}`.toLowerCase();
  }

  const context = document.createElement("canvas").getContext("2d");
  if (!context) return undefined;

  context.fillStyle = "#000000";
  context.fillStyle = trimmed;
  const parsed = context.fillStyle;

  return typeof parsed === "string" && /^#[0-9a-f]{6}$/i.test(parsed)
    ? parsed
    : undefined;
}

/** Whether a value looks like a CSS gradient or image rather than a colour. */
export function isGradientValue(value?: string): boolean {
  return Boolean(value && /gradient\(|url\(/i.test(value));
}
