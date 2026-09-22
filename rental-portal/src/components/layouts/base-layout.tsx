"use client";

/**
 * Portal page shell: sidebar, site header, page title and the theme customizer.
 *
 * The theme customizer is mounted with the shell (closed by default) and opened
 * from the user menu, exactly like the nppos dashboard. It restores the saved
 * theme itself, so no separate persistence layer is needed here.
 */

import { AppSidebar } from "@/components/app-sidebar";
import { SiteHeader } from "@/components/site-header";
import { ThemeCustomizer } from "@/components/theme-customizer";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useSidebarConfig } from "@/hooks/use-sidebar-config";
import * as React from "react";

interface BaseLayoutProps {
  /** Page content; optional so a layout-only page (placeholder) can be rendered. */
  children?: React.ReactNode;
  title?: string;
  description?: string;
}

export function BaseLayout({ children, title, description }: BaseLayoutProps) {
  const [themeCustomizerOpen, setThemeCustomizerOpen] = React.useState(false);
  const { config } = useSidebarConfig();

  const openThemeCustomizer = React.useCallback(
    () => setThemeCustomizerOpen(true),
    [],
  );

  return (
    <>
      <SidebarProvider
        style={
          {
            "--sidebar-width": "16rem",
            "--sidebar-width-icon": "3rem",
            "--header-height": "calc(var(--spacing) * 14)",
          } as React.CSSProperties
        }
        className={config.collapsible === "none" ? "sidebar-none-mode" : ""}
      >
        {config.side === "left" ? (
          <>
            <AppSidebar
              variant={config.variant}
              collapsible={config.collapsible}
              side={config.side}
              onOpenCustomizer={openThemeCustomizer}
            />
            <SidebarInset>
              <SiteHeader />
              <div className="flex flex-1 flex-col">
                <div className="@container/main flex flex-1 flex-col gap-2">
                  <div className="page-enter flex flex-col gap-4 py-4 md:gap-6 md:py-6">
                    {title && (
                      <div className="px-4 lg:px-6">
                        <div className="flex flex-col gap-2">
                          <h1 className="text-2xl font-bold tracking-tight">
                            {title}
                          </h1>
                          {description && (
                            <p className="text-muted-foreground">{description}</p>
                          )}
                        </div>
                      </div>
                    )}
                    {children}
                  </div>
                </div>
              </div>
            </SidebarInset>
          </>
        ) : (
          <>
            <SidebarInset>
              <SiteHeader />
              <div className="flex flex-1 flex-col">
                <div className="@container/main flex flex-1 flex-col gap-2">
                  <div className="page-enter flex flex-col gap-4 py-4 md:gap-6 md:py-6">
                    {title && (
                      <div className="px-4 lg:px-6">
                        <div className="flex flex-col gap-2">
                          <h1 className="text-2xl font-bold tracking-tight">
                            {title}
                          </h1>
                          {description && (
                            <p className="text-muted-foreground">{description}</p>
                          )}
                        </div>
                      </div>
                    )}
                    {children}
                  </div>
                </div>
              </div>
            </SidebarInset>
            <AppSidebar
              variant={config.variant}
              collapsible={config.collapsible}
              side={config.side}
              onOpenCustomizer={openThemeCustomizer}
            />
          </>
        )}
        {/* Mounted inside SidebarProvider: the customizer's Layout tab drives the
            sidebar through `useSidebar()`. */}
        <ThemeCustomizer
          open={themeCustomizerOpen}
          onOpenChange={setThemeCustomizerOpen}
        />
      </SidebarProvider>
    </>
  );
}

