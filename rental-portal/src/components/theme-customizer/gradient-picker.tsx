"use client";

/**
 * Gradient picker for one themeable surface.
 *
 * Offers the built-in blends (which are generated from the surface's own tokens
 * so they harmonise in both modes) plus a free text field for any custom CSS
 * gradient. Selecting "None" writes `none`, overriding a gradient that came
 * from the preset.
 */

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { GradientSurface } from "@/types/theme-customizer";
import {
  buildGradient,
  gradientVariants,
  matchGradientVariant,
  type GradientVariant,
} from "@/utils/theme-gradients";
import { cn } from "@/lib/utils";

interface GradientPickerProps {
  surface: GradientSurface;
  label: string;
  /** Resolved gradient value currently in effect for the edited mode. */
  value?: string;
  /** Preview background colour of the surface. */
  previewColor?: string;
  onChange: (surface: GradientSurface, value: string) => void;
}

export function GradientPicker({
  surface,
  label,
  value,
  previewColor,
  onChange,
}: GradientPickerProps) {
  const active = matchGradientVariant(surface, value);
  const [custom, setCustom] = React.useState(
    active === "custom" ? (value ?? "") : "",
  );

  React.useEffect(() => {
    setCustom(active === "custom" ? (value ?? "") : "");
  }, [active, value]);

  const select = (variant: GradientVariant) => {
    if (variant === "custom") {
      onChange(surface, custom.trim() || "none");
      return;
    }
    onChange(surface, buildGradient(surface, variant) ?? "none");
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Label className="text-xs font-medium">{label}</Label>
        <span className="text-muted-foreground font-mono text-[10px]">
          {active === "custom" ? "custom" : active}
        </span>
      </div>

      <div
        className="border-border h-14 w-full rounded-md border"
        style={{ backgroundColor: previewColor, backgroundImage: value ?? undefined }}
        aria-hidden
      />

      <div className="grid grid-cols-3 gap-1.5">
        {gradientVariants.map((variant) => (
          <Button
            key={variant.value}
            type="button"
            size="sm"
            variant={active === variant.value ? "secondary" : "outline"}
            title={variant.description}
            onClick={() => select(variant.value)}
            className={cn(
              "h-7 cursor-pointer px-1 text-[11px]",
              active === variant.value && "border-primary",
            )}
          >
            {variant.label}
          </Button>
        ))}
      </div>

      <Input
        value={custom}
        placeholder="linear-gradient(135deg, var(--primary), var(--accent))"
        onChange={(event) => setCustom(event.target.value)}
        onBlur={() => select("custom")}
        onKeyDown={(event) => {
          if (event.key === "Enter") select("custom");
        }}
        className="h-7 font-mono text-[11px]"
      />
    </div>
  );
}
