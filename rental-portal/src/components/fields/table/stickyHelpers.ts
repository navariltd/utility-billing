"use client";

/**
 * Sticky left cell – fully opaque background so content underneath doesn't show through.
 */
export const STICKY_CELL_CLASS =
  "sticky left-0 z-10 bg-background after:absolute after:inset-y-0 after:right-0 after:w-px after:bg-border";

/**
 * Sticky right action cell – fully opaque background.
 */
export const STICKY_RIGHT_CLASS =
  "sticky right-0 z-20 bg-background after:absolute after:inset-y-0 after:left-0 after:w-px after:bg-border";

/**
 * Sticky right action column header – fully opaque background (use bg-background, not transparent).
 */
export const STICKY_RIGHT_HEADER_CLASS =
  "sticky right-0 z-20 bg-background after:absolute after:inset-y-0 after:left-0 after:w-px after:bg-border";

export const getStickyStyle = (colIndex: number, stickyCount: number) => {
  if (colIndex >= stickyCount) return undefined;
  const offset = colIndex * 140;
  return { left: `${offset}px` } as React.CSSProperties;
};