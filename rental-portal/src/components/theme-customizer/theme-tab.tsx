"use client";

/**
 * Theme tab of the customizer.
 *
 * Reading order: pick a complete preset, switch the appearance, tune the
 * colours and gradients of each mode, then adjust shape and import a theme.
 * All state comes from `ThemeEditorProvider`.
 */

import { EstatePresetGrid } from "@/components/theme-customizer/estate-preset-grid";
import { PresetSelect } from "@/components/theme-customizer/preset-select";
import { ThemeColorEditor } from "@/components/theme-customizer/theme-color-editor";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { radiusOptions } from "@/config/theme-customizer-constants";
import { useThemeEditor } from "@/contexts/theme-editor-context";
import { useCircularTransition } from "@/hooks/use-circular-transition";
import type { ColorTheme } from "@/types/theme-customizer";
import type { ThemeFamily } from "@/utils/theme-storage";
import { Moon, Sun, Upload } from "lucide-react";
import React from "react";
import "./circular-transition.css";

interface ThemeTabProps {
  onImportClick: () => void;
}

export function ThemeTab({ onImportClick }: ThemeTabProps) {
  const {
    isDarkMode,
    setDarkMode,
    family,
    preset,
    radius,
    setRadius,
    shadcnPresets,
    tweakcnPresets,
    applyPreset,
    clearPreset,
  } = useThemeEditor();

  const { startTransition } = useCircularTransition();

  const applyRandom = (target: ThemeFamily, list: ColorTheme[]) => {
    if (list.length === 0) return;
    const index = Math.floor(Math.random() * list.length);
    applyPreset(target, list[index].value);
  };

  const handleMode = (
    event: React.MouseEvent<HTMLButtonElement>,
    dark: boolean,
  ) => {
    if (dark === isDarkMode) return;
    startTransition({ x: event.clientX, y: event.clientY }, () =>
      setDarkMode(dark),
    );
  };

  return (
    <div className="p-4 space-y-6">
      {/* Built-in property theme presets */}
      <EstatePresetGrid />

      <Separator />

      {/* Appearance */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Appearance</Label>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant={isDarkMode ? "outline" : "secondary"}
            size="sm"
            onClick={(event) => handleMode(event, false)}
            className="cursor-pointer mode-toggle-button relative overflow-hidden"
          >
            <Sun className="h-4 w-4 mr-1 transition-transform duration-300" />
            Light
          </Button>
          <Button
            variant={isDarkMode ? "secondary" : "outline"}
            size="sm"
            onClick={(event) => handleMode(event, true)}
            className="cursor-pointer mode-toggle-button relative overflow-hidden"
          >
            <Moon className="h-4 w-4 mr-1 transition-transform duration-300" />
            Dark
          </Button>
        </div>
      </div>

      <Separator />

      {/* Classic preset families */}
      <div className="space-y-4">
        <PresetSelect
          label="Shadcn UI Theme Presets"
          placeholder="Choose Shadcn Theme"
          themes={shadcnPresets}
          value={family === "shadcn" ? preset : ""}
          onValueChange={(value) => applyPreset("shadcn", value)}
          onRandom={() => applyRandom("shadcn", shadcnPresets)}
          darkMode={isDarkMode}
        />

        <PresetSelect
          label="Tweakcn Theme Presets"
          placeholder="Choose Tweakcn Theme"
          themes={tweakcnPresets}
          value={family === "tweakcn" ? preset : ""}
          onValueChange={(value) => applyPreset("tweakcn", value)}
          onRandom={() => applyRandom("tweakcn", tweakcnPresets)}
          darkMode={isDarkMode}
        />

        <Button
          variant={family === "" ? "secondary" : "outline"}
          size="sm"
          onClick={clearPreset}
          className="w-full cursor-pointer"
        >
          Portal default colours
        </Button>
      </div>

      <Separator />

      {/* Colours and gradients, per mode */}
      <ThemeColorEditor />

      <Separator />

      {/* Radius Selection */}
      <div className="space-y-3">
        <Label className="text-sm font-medium">Radius</Label>
        <div className="grid grid-cols-5 gap-2">
          {radiusOptions.map((option) => (
            <div
              key={option.value}
              className={`relative cursor-pointer rounded-md p-3 border transition-colors ${
                radius === option.value
                  ? "border-primary"
                  : "border-border hover:border-border/60"
              }`}
              onClick={() => setRadius(option.value)}
            >
              <div className="text-center">
                <div className="text-xs font-medium">{option.name}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Import Theme Button */}
      <div className="space-y-3">
        <Button
          variant="outline"
          size="lg"
          onClick={onImportClick}
          className="w-full cursor-pointer"
        >
          <Upload className="h-3.5 w-3.5 mr-1.5" />
          Import Theme
        </Button>
      </div>
    </div>
  );
}
