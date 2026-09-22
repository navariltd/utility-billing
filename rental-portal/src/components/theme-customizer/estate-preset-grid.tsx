"use client";

/**
 * Picker for the built-in property themes.
 *
 * Renders every preset as a miniature of the interface – sidebar, page, card
 * and the brand colours – in a searchable grid so a large preset library stays
 * scannable. Presets are flat by default; gradients are added by the user in
 * the colour editor.
 */

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useThemeEditor } from "@/contexts/theme-editor-context";
import { cn } from "@/lib/utils";
import type { ColorTheme } from "@/types/theme-customizer";
import { Check, Search, Star } from "lucide-react";
import * as React from "react";

export function EstatePresetGrid() {
  const { estatePresets, preset, family, applyPreset, isDarkMode } =
    useThemeEditor();
  const [query, setQuery] = React.useState("");
  const mode = isDarkMode ? "dark" : "light";

  const filtered = React.useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return estatePresets;

    return estatePresets.filter((theme) =>
      [theme.name, theme.description ?? "", theme.value]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [estatePresets, query]);

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <Label className="text-sm font-medium">Property Themes</Label>
        <p className="text-muted-foreground text-xs">
          {estatePresets.length} flat presets – apply one, then add gradients and
          tune every colour below.
        </p>
      </div>

      <div className="relative">
        <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2" />
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`Search ${estatePresets.length} themes`}
          className="h-8 pl-8 text-xs"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        {filtered.map((theme) => (
          <PresetCard
            key={theme.value}
            theme={theme}
            mode={mode}
            selected={family === "estate" && preset === theme.value}
            onSelect={() => applyPreset("estate", theme.value)}
          />
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted-foreground text-xs">
          No theme matches “{query.trim()}”.{" "}
          <button
            type="button"
            onClick={() => setQuery("")}
            className="text-primary cursor-pointer underline underline-offset-2"
          >
            Clear search
          </button>
        </p>
      ) : null}
    </div>
  );
}

interface PresetCardProps {
  theme: ColorTheme;
  mode: "light" | "dark";
  selected: boolean;
  onSelect: () => void;
}

function PresetCard({ theme, mode, selected, onSelect }: PresetCardProps) {
  const styles: Record<string, string> = theme.preset.styles[mode] ?? {};

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      title={`${theme.name} – ${theme.description}`}
      className={cn(
        "group cursor-pointer rounded-xl border p-2 text-left transition-all duration-200",
        "hover:-translate-y-0.5 hover:shadow-lg",
        selected
          ? "border-primary ring-primary/50 bg-primary/5 shadow-md ring-2"
          : "border-border hover:border-primary/50",
      )}
    >
      {/* Miniature of the interface, drawn with the preset's own tokens so the
          palette (and any gradient set for a surface) is visible at full
          opacity. */}
      <div className="flex h-16 overflow-hidden rounded-lg border border-black/10">
        <div
          className="flex w-1/4 flex-col gap-1 border-r border-black/10 p-1.5"
          style={{
            backgroundColor: styles.sidebar,
            backgroundImage: styles["sidebar-gradient"],
          }}
          aria-hidden
        >
          <span
            className="block h-1.5 w-full rounded-full"
            style={{ backgroundColor: styles["sidebar-foreground"] }}
          />
          <span
            className="block h-1.5 w-full rounded-full"
            style={{ backgroundColor: styles["sidebar-accent"] }}
          />
          <span
            className="block h-1.5 w-2/3 rounded-full"
            style={{
              backgroundColor: styles["sidebar-foreground"],
              opacity: 0.5,
            }}
          />
        </div>

        <div
          className="flex flex-1 flex-col justify-between p-1.5"
          style={{
            backgroundColor: styles.background,
            backgroundImage: styles["background-gradient"],
          }}
          aria-hidden
        >
          <span
            className="block h-7 w-full rounded-md border"
            style={{ backgroundColor: styles.card, borderColor: styles.border }}
          />
          <span className="flex items-center gap-1">
            <span
              className="h-2 flex-1 rounded-full"
              style={{
                backgroundColor: styles.primary,
                backgroundImage: styles["primary-gradient"],
              }}
            />
            <span
              className="h-2 w-3 rounded-full"
              style={{ backgroundColor: styles.accent }}
            />
            <span
              className="h-2 w-3 rounded-full"
              style={{ backgroundColor: styles.secondary }}
            />
          </span>
        </div>
      </div>

      <div className="mt-1.5 flex items-center gap-1">
        <span className="truncate text-[11px] font-medium">{theme.name}</span>
        {selected ? (
          <Check className="text-primary ml-auto size-3 shrink-0" />
        ) : theme.recommended ? (
          <Star
            className="text-muted-foreground ml-auto size-3 shrink-0"
            aria-label="Portal default"
          />
        ) : null}
      </div>
      <p className="text-muted-foreground truncate text-[10px]">
        {theme.description}
      </p>
    </button>
  );
}
