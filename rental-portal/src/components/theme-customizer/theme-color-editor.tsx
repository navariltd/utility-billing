"use client";

/**
 * Colour and gradient editor for the theme.
 *
 * Edits one mode at a time (the mode switch also follows the app appearance) so
 * light and dark can be tuned independently, with every token grouped by the
 * part of the interface it drives. Changes are stored as overrides on top of the
 * selected preset.
 */

import { ColorPicker } from "@/components/color-picker";
import { GradientPicker } from "@/components/theme-customizer/gradient-picker";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  defaultOpenTokenGroups,
  editableTokens,
  gradientTokens,
  themeTokenGroups,
} from "@/config/theme-token-groups";
import { useThemeEditor } from "@/contexts/theme-editor-context";
import type { GradientSurface, ThemeMode } from "@/types/theme-customizer";
import { modeLabel } from "@/utils/theme-tokens";
import { Copy, Moon, RotateCcw, Sun } from "lucide-react";
import * as React from "react";

/** Surface colour previewed behind each gradient. */
const GRADIENT_PREVIEW: Record<GradientSurface, string> = {
  page: "background",
  sidebar: "sidebar",
  brand: "primary",
};

export function ThemeColorEditor() {
  const {
    editMode,
    setEditMode,
    tokens,
    overrides,
    setToken,
    setGradient,
    copyModeToOther,
    resetMode,
  } = useThemeEditor();

  const resolved = tokens(editMode);
  const current = overrides[editMode] ?? {};
  const otherMode: ThemeMode = editMode === "dark" ? "light" : "dark";
  const overrideCount = Object.keys(current).length;

  // Tokens no preset defines (the semantic state colours) resolve from
  // `index.css`; show those values so no field is ever blank for a colour the
  // interface is actually using.
  const [cssDefaults, setCssDefaults] = React.useState<Record<string, string>>(
    {},
  );

  React.useEffect(() => {
    const root = getComputedStyle(document.documentElement);
    const next: Record<string, string> = {};

    for (const token of editableTokens) {
      if (resolved[token]) continue;
      const value = root.getPropertyValue(`--${token}`).trim();
      if (value) next[token] = value;
    }

    setCssDefaults((previous) =>
      JSON.stringify(previous) === JSON.stringify(next) ? previous : next,
    );
  }, [resolved]);

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="grid grid-cols-2 gap-1 rounded-lg border p-1">
            {(["light", "dark"] as ThemeMode[]).map((mode) => (
              <Button
                key={mode}
                type="button"
                size="sm"
                variant={editMode === mode ? "secondary" : "ghost"}
                onClick={() => setEditMode(mode)}
                className="h-7 cursor-pointer gap-1.5 px-3 text-xs"
              >
                {mode === "dark" ? (
                  <Moon className="h-3.5 w-3.5" />
                ) : (
                  <Sun className="h-3.5 w-3.5" />
                )}
                {modeLabel(mode)}
              </Button>
            ))}
          </div>

          {overrideCount > 0 ? (
            <Badge variant="secondary" className="text-[10px]">
              {overrideCount} custom
            </Badge>
          ) : null}
        </div>

        <p className="text-muted-foreground text-xs">
          Editing <span className="text-foreground font-medium">{modeLabel(editMode)}</span>{" "}
          colours – they are used whenever the portal is in {modeLabel(editMode).toLowerCase()}{" "}
          mode. Gradients are opt in and apply to both modes.
        </p>
      </div>

      <div className="flex gap-1.5">
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => copyModeToOther(editMode)}
          className="h-7 flex-1 cursor-pointer text-[11px]"
        >
          <Copy className="mr-1 h-3 w-3" />
          Copy to {modeLabel(otherMode).toLowerCase()}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={overrideCount === 0}
          onClick={() => resetMode(editMode)}
          className="h-7 flex-1 cursor-pointer text-[11px]"
        >
          <RotateCcw className="mr-1 h-3 w-3" />
          Reset {modeLabel(editMode).toLowerCase()}
        </Button>
      </div>

      <Accordion
        type="multiple"
        defaultValue={defaultOpenTokenGroups}
        className="space-y-2"
      >
        {themeTokenGroups.map((group) => (
          <AccordionItem
            key={group.id}
            value={group.id}
            className="border-border rounded-lg border"
          >
            <AccordionTrigger className="hover:bg-muted/50 px-3 py-2.5 text-left transition-colors hover:no-underline">
              <span className="flex flex-col items-start gap-0.5">
                <span className="text-sm font-medium">{group.label}</span>
                <span className="text-muted-foreground text-[11px] font-normal">
                  {group.description}
                </span>
              </span>
            </AccordionTrigger>
            <AccordionContent className="border-border space-y-3 border-t px-3 pt-3 pb-3">
              {group.gradients?.map((surface) => (
                <GradientPicker
                  key={surface}
                  surface={surface}
                  label={`${capitalize(surface)} gradient`}
                  value={resolved[gradientTokens[surface]]}
                  previewColor={resolved[GRADIENT_PREVIEW[surface]]}
                  onChange={setGradient}
                />
              ))}

              {group.tokens.map((token) => (
                <ColorPicker
                  key={token.token}
                  label={token.name}
                  token={token.token}
                  hint={token.hint}
                  value={resolved[token.token] ?? cssDefaults[token.token] ?? ""}
                  modified={current[token.token] !== undefined}
                  onChange={(target, value) => setToken(editMode, target, value)}
                  onReset={(target) => setToken(editMode, target, "")}
                />
              ))}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
