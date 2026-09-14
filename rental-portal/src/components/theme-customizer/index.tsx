"use client";

/**
 * Theme customizer sheet.
 *
 * Only the shell lives here: tabs, the reset action and the theme import modal.
 * All theme state and the colour editors come from `ThemeEditorProvider`, and
 * the sheet is opened from the user menu by `BaseLayout`.
 */

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSidebarConfig } from "@/contexts/sidebar-context";
import { useThemeEditor } from "@/contexts/theme-editor-context";
import { cn } from "@/lib/utils";
import { Layout, Palette, RotateCcw, Settings, X } from "lucide-react";
import React from "react";
import { ImportModal } from "./import-modal";
import { LayoutTab } from "./layout-tab";
import { ThemeTab } from "./theme-tab";

interface ThemeCustomizerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const OPEN_GRACE_MS = 400;

export function ThemeCustomizer({ open, onOpenChange }: ThemeCustomizerProps) {
  const { config: sidebarConfig, updateConfig: updateSidebarConfig } =
    useSidebarConfig();
  const { importTheme, resetTheme, hasOverrides, family, preset } =
    useThemeEditor();

  const [activeTab, setActiveTab] = React.useState("theme");
  const [importModalOpen, setImportModalOpen] = React.useState(false);
  const openedAtRef = React.useRef(0);

  React.useEffect(() => {
    if (open) openedAtRef.current = Date.now();
  }, [open]);

  const handleReset = () => {
    resetTheme();
    updateSidebarConfig({ variant: "inset", collapsible: "icon", side: "left" });
  };

  const handleImportClick = () => setImportModalOpen(true);

  return (
    <>
      {/* Non modal: no overlay, the page stays visible and usable behind the
          panel, and clicking outside closes it (the preview stays live). */}
      <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
        <SheetContent
          side={sidebarConfig.side === "left" ? "right" : "left"}
          showOverlay={false}
          className="w-[420px] p-0 gap-0 [&>button]:hidden overflow-hidden flex flex-col shadow-2xl pointer-events-auto"
          onInteractOutside={(event) => {
            // The trigger lives in a dropdown menu that hands focus back to its
            // button as the panel opens; that interaction must not dismiss the
            // panel, only a deliberate click outside it should.
            if (Date.now() - openedAtRef.current < OPEN_GRACE_MS) {
              event.preventDefault();
            }
          }}
        >
          <SheetHeader className="space-y-0 p-4 pb-2">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Settings className="h-4 w-4" />
              </div>
              <div className="flex flex-col">
                <SheetTitle className="text-lg font-semibold">
                  Customize Theme
                </SheetTitle>
                {family === "imported" ? (
                  <span className="text-muted-foreground text-[11px]">
                    Imported theme
                  </span>
                ) : hasOverrides ? (
                  <span className="text-muted-foreground text-[11px]">
                    {preset || "portal default"} · custom colours
                  </span>
                ) : null}
              </div>
              <div className="ml-auto flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleReset}
                  title="Reset theme and layout"
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
              Customize the theme and layout of your dashboard.
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
              </div>
              <TabsContent value="theme" className="flex-1 mt-0">
                <ThemeTab onImportClick={handleImportClick} />
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
        onImport={importTheme}
      />
    </>
  );
}

/** Floating trigger button - positioned dynamically based on sidebar side. */
export function ThemeCustomizerTrigger({ onClick }: { onClick: () => void }) {
  const { config: sidebarConfig } = useSidebarConfig();

  return (
    <Button
      onClick={onClick}
      size="icon"
      className={cn(
        "fixed top-1/2 -translate-y-1/2 h-12 w-12 rounded-full shadow-lg z-50 bg-primary bg-brand-gradient hover:bg-primary/90 text-primary-foreground cursor-pointer",
        sidebarConfig.side === "left" ? "right-4" : "left-4",
      )}
    >
      <Settings className="h-5 w-5" />
    </Button>
  );
}
