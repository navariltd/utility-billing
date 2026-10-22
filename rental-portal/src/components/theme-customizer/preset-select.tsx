"use client";

/**
 * Dropdown preset picker with colour swatches.
 *
 * Used for the shadcn and Tweakcn preset families, which are long lists that
 * read better in a select than as cards.
 */

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ColorTheme } from "@/types/theme-customizer";
import { Dices } from "lucide-react";

/** Swatches previewed next to each option. */
const SWATCH_TOKENS = ["primary", "secondary", "accent", "muted"] as const;

interface PresetSelectProps {
  label: string;
  placeholder: string;
  themes: ColorTheme[];
  value: string;
  onValueChange: (value: string) => void;
  /** Picks a random preset from `themes`. */
  onRandom: () => void;
  /** Read the swatches from each preset's dark variant. */
  darkMode: boolean;
}

export function PresetSelect({
  label,
  placeholder,
  themes,
  value,
  onValueChange,
  onRandom,
  darkMode,
}: PresetSelectProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{label}</Label>
        <Button
          variant="outline"
          size="sm"
          onClick={onRandom}
          className="cursor-pointer"
        >
          <Dices className="mr-1.5 h-3.5 w-3.5" />
          Random
        </Button>
      </div>

      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className="w-full cursor-pointer">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="max-h-60">
          <div className="p-2">
            {themes.map((theme) => {
              const styles = darkMode
                ? theme.preset.styles.dark
                : theme.preset.styles.light;

              return (
                <SelectItem
                  key={theme.value}
                  value={theme.value}
                  className="cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      {SWATCH_TOKENS.map((token) => (
                        <div
                          key={token}
                          className="border-border/20 h-3 w-3 rounded-full border"
                          style={{ backgroundColor: styles[token] }}
                        />
                      ))}
                    </div>
                    <span>{theme.name}</span>
                  </div>
                </SelectItem>
              );
            })}
          </div>
        </SelectContent>
      </Select>
    </div>
  );
}
