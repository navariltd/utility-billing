/**
 * Grid / list layout switcher for property collections.
 */

"use client";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { LayoutGrid, List } from "lucide-react";

import type { PropertyLayout } from "./types";

interface LayoutToggleProps {
  value: PropertyLayout;
  onChange: (layout: PropertyLayout) => void;
}

export function LayoutToggle({ value, onChange }: LayoutToggleProps) {
  return (
    <ToggleGroup
      type="single"
      size="sm"
      variant="outline"
      value={value}
      onValueChange={(next) => {
        // Ignore deselection so one layout is always active.
        if (next === "grid" || next === "list") {
          onChange(next);
        }
      }}
      aria-label="Property layout"
    >
      <ToggleGroupItem value="grid" aria-label="Grid layout" className="cursor-pointer">
        <LayoutGrid className="h-4 w-4" />
      </ToggleGroupItem>
      <ToggleGroupItem value="list" aria-label="List layout" className="cursor-pointer">
        <List className="h-4 w-4" />
      </ToggleGroupItem>
    </ToggleGroup>
  );
}
