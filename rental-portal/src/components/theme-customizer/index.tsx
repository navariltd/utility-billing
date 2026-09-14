"use client";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { tweakcnThemes } from "@/config/theme-data";
import { useSidebarConfig } from "@/contexts/sidebar-context";
import { useThemeManager } from "@/hooks/use-theme-manager";
import { cn } from "@/lib/utils";
import type { ImportedTheme } from "@/types/theme-customizer";
import { Layout, Palette, RotateCcw, Settings, X } from "lucide-react";
import React from "react";
import { ImportModal } from "./import-modal";
import { LayoutTab } from "./layout-tab";
import { ThemeTab } from "./theme-tab";

const STORAGE_KEY = "rental-portal:theme";

interface SavedThemeState {
  selectedTheme: string;
  selectedTweakcnTheme: string;
  selectedRadius: string;
  importedTheme: ImportedTheme | null;
}

function loadSavedTheme(): SavedThemeState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveThemeState(state: SavedThemeState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore
  }
}

interface ThemeCustomizerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ThemeCustomizer({ open, onOpenChange }: ThemeCustomizerProps) {
  const {
    applyImportedTheme,
    isDarkMode,
    resetTheme,
    applyRadius,
    setBrandColorsValues,
    applyTheme,
    applyTweakcnTheme,
  } = useThemeManager();
  const { config: sidebarConfig, updateConfig: updateSidebarConfig } =
    useSidebarConfig();

  const [activeTab, setActiveTab] = React.useState("theme");
  const [selectedTheme, setSelectedTheme] = React.useState("default");
  const [selectedTweakcnTheme, setSelectedTweakcnTheme] = React.useState("");
  const [selectedRadius, setSelectedRadius] = React.useState("0.5rem");
  const [importModalOpen, setImportModalOpen] = React.useState(false);
  const [importedTheme, setImportedTheme] =
    React.useState<ImportedTheme | null>(null);
  const [hydrated, setHydrated] = React.useState(false);

  // Load saved state on mount and apply it
  React.useEffect(() => {
    const saved = loadSavedTheme();
    if (saved) {
      setSelectedTheme(saved.selectedTheme ?? "");
      setSelectedTweakcnTheme(saved.selectedTweakcnTheme ?? "");
      setSelectedRadius(saved.selectedRadius ?? "0.5rem");
      if (saved.importedTheme) {
        setImportedTheme(saved.importedTheme);
      }
    }
    setHydrated(true);
  }, []);

  // Apply theme after hydration + whenever a selection or dark mode changes
  React.useEffect(() => {
    if (!hydrated) return;
    if (importedTheme) {
      applyImportedTheme(importedTheme, isDarkMode);
      saveThemeState({ selectedTheme, selectedTweakcnTheme, selectedRadius, importedTheme });
    } else if (selectedTheme) {
      applyTheme(selectedTheme, isDarkMode);
      saveThemeState({ selectedTheme, selectedTweakcnTheme, selectedRadius, importedTheme: null });
    } else if (selectedTweakcnTheme) {
      const selectedPreset = tweakcnThemes.find(
        (t) => t.value === selectedTweakcnTheme,
      )?.preset;
      if (selectedPreset) {
        applyTweakcnTheme(selectedPreset, isDarkMode);
        saveThemeState({ selectedTheme, selectedTweakcnTheme, selectedRadius, importedTheme: null });
      }
    }
  }, [hydrated, isDarkMode, importedTheme, selectedTheme, selectedTweakcnTheme, applyImportedTheme, applyTheme, applyTweakcnTheme]);

  const handleReset = () => {
    // Complete reset to application defaults

    // 1. Reset all state variables to initial values
    setSelectedTheme(""); // Clear theme selection after reset
    setSelectedTweakcnTheme("");
    setSelectedRadius("0.5rem");
    setImportedTheme(null); // Clear imported theme
    setBrandColorsValues({}); // Clear brand colors state

    // 2. Completely remove all custom CSS variables
    resetTheme();

    // 3. Reset the radius to default
    applyRadius("0.5rem");

    // 4. Reset sidebar to defaults
    updateSidebarConfig({
      variant: "inset",
      collapsible: "icon",
      side: "left",
    });

    // 5. Clear saved state
    saveThemeState({ selectedTheme: "", selectedTweakcnTheme: "", selectedRadius: "0.5rem", importedTheme: null });
  };

  const handleImport = (themeData: ImportedTheme) => {
    setImportedTheme(themeData);
    // Clear other selections to indicate custom import is active
    setSelectedTheme("");
    setSelectedTweakcnTheme("");
    // Apply and persist via the effect
  };

  const handleImportClick = () => {
    setImportModalOpen(true);
  };

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side={sidebarConfig.side === "left" ? "right" : "left"}
          className="w-[400px] p-0 gap-0 [&>button]:hidden overflow-hidden flex flex-col"
          onInteractOutside={(e) => {
            // Prevent outside clicks from closing the Customizer.
            // Only close via the X button or toggling the menu item.
            e.preventDefault();
          }}
          onEscapeKeyDown={() => {
            // Allow Escape to close
          }}
        >
          <SheetHeader className="space-y-0 p-4 pb-2">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Settings className="h-4 w-4" />
              </div>
              <SheetTitle className="text-lg font-semibold">
                Customize Theme
              </SheetTitle>
              <div className="ml-auto flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleReset}
                  className="cursor-pointer h-8 w-8"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => onOpenChange(false)}
                  className="cursor-pointer h-8 w-8"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <SheetDescription className="text-sm text-muted-foreground sr-only">
              Customize the them and layout of your dashboard.
            </SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto">
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="h-full flex flex-col"
            >
              <div className="py-2">
                <TabsList className="grid w-full grid-cols-2 rounded-none h-12 p-1.5">
                  <TabsTrigger
                    value="theme"
                    className="cursor-pointer data-[state=active]:bg-background"
                  >
                    <Palette className="h-4 w-4 mr-1" /> Theme
                  </TabsTrigger>
                  <TabsTrigger
                    value="layout"
                    className="cursor-pointer data-[state=active]:bg-background"
                  >
                    <Layout className="h-4 w-4 mr-1" /> Layout
                  </TabsTrigger>
                </TabsList>
                {/* <TabsList className="grid w-full grid-cols-2 rounded-none h-12 p-1.5">
                  <TabsTrigger value="theme" className="cursor-pointer data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Palette className="h-4 w-4 mr-1" /> Theme</TabsTrigger>
                  <TabsTrigger value="layout" className="cursor-pointer data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"><Layout className="h-4 w-4 mr-1" /> Layout</TabsTrigger>
                </TabsList> */}
              </div>

              <TabsContent value="theme" className="flex-1 mt-0">
                <ThemeTab
                  selectedTheme={selectedTheme}
                  setSelectedTheme={setSelectedTheme}
                  selectedTweakcnTheme={selectedTweakcnTheme}
                  setSelectedTweakcnTheme={setSelectedTweakcnTheme}
                  selectedRadius={selectedRadius}
                  setSelectedRadius={setSelectedRadius}
                  setImportedTheme={setImportedTheme}
                  onImportClick={handleImportClick}
                />
              </TabsContent>

              <TabsContent value="layout" className="flex-1 mt-0">
                <LayoutTab />
              </TabsContent>
            </Tabs>
          </div>
        </SheetContent>
      </Sheet>

      <ImportModal
        open={importModalOpen}
        onOpenChange={setImportModalOpen}
        onImport={handleImport}
      />
    </>
  );
}

// Floating trigger button - positioned dynamically based on sidebar side
export function ThemeCustomizerTrigger({ onClick }: { onClick: () => void }) {
  const { config: sidebarConfig } = useSidebarConfig();

  return (
    <Button
      onClick={onClick}
      size="icon"
      className={cn(
        "fixed top-1/2 -translate-y-1/2 h-12 w-12 rounded-full shadow-lg z-50 bg-primary hover:bg-primary/90 text-primary-foreground cursor-pointer",
        sidebarConfig.side === "left" ? "right-4" : "left-4",
      )}
    >
      <Settings className="h-5 w-5" />
    </Button>
  );
}
