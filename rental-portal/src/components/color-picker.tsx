"use client";

/**
 * Colour field for a single design token.
 *
 * Accepts any CSS colour value: the swatch previews whatever is typed (so
 * `oklch()`, gradients and `color-mix()` render correctly) while the native
 * picker works on the closest hex. Tokens that differ from the selected preset
 * offer a reset back to the preset value.
 */

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cssColorToHex } from "@/utils/css-color";
import { RotateCcw } from "lucide-react";

interface ColorPickerProps {
  label: string;
  /** Token name without the leading `--`, e.g. `sidebar-accent`. */
  token: string;
  value: string;
  /** Example value shown when the token is unset. */
  hint?: string;
  /** True when the value differs from the preset (enables the reset action). */
  modified?: boolean;
  onChange: (token: string, value: string) => void;
  onReset?: (token: string) => void;
}

export function ColorPicker({
  label,
  token,
  value,
  hint,
  modified,
  onChange,
  onReset,
}: ColorPickerProps) {
  const [draft, setDraft] = React.useState(value);
  const [pickerHex, setPickerHex] = React.useState("#000000");

  React.useEffect(() => {
    setDraft(value);
  }, [value]);

  // Keep the native picker on the closest hex of the current value.
  React.useEffect(() => {
    const parsed =
      cssColorToHex(draft) ??
      cssColorToHex(
        getComputedStyle(document.documentElement).getPropertyValue(`--${token}`),
      );
    if (parsed) setPickerHex(parsed);
  }, [draft, token]);

  const handleColorChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setDraft(event.target.value);
    onChange(token, event.target.value);
  };

  const handleTextChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setDraft(event.target.value);
    onChange(token, event.target.value);
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={`token-${token}`} className="text-xs font-medium">
          {label}
        </Label>
        {modified && onReset ? (
          <button
            type="button"
            title="Reset to the preset value"
            onClick={() => onReset(token)}
            className="text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <RotateCcw className="h-3 w-3" />
          </button>
        ) : null}
      </div>

      <div className="flex items-start gap-2">
        <div className="relative shrink-0">
          <Button
            type="button"
            variant="outline"
            aria-label={`${label} colour`}
            className="h-8 w-8 overflow-hidden p-0 cursor-pointer"
            style={{ background: draft || "transparent" }}
          >
            <input
              type="color"
              id={`token-${token}`}
              value={pickerHex}
              onChange={handleColorChange}
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
            />
          </Button>
        </div>
        <Input
          type="text"
          placeholder={hint ?? `--${token}`}
          value={draft}
          onChange={handleTextChange}
          className="h-8 flex-1 font-mono text-xs"
        />
      </div>
    </div>
  );
}
