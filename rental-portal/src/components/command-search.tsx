"use client";

import {
  ChevronDown,
  ChevronUp,
  FileSearch,
  FolderOpen,
  Search,
  SlidersHorizontal,
  Tags,
  X,
} from "lucide-react";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import * as React from "react";
import { useNavigate } from "react-router-dom";

import { APP_PAGES_ENABLED, routes, type RouteConfig } from "@/config/routes";
import { doctypeToSlug } from "@/lib/doctype-map";
import { getBootUser } from "@/lib/portal";

interface SearchItem {
  title: string;
  url?: string;
  group: string;
  /** For global search results */
  doctype?: string;
  name?: string;
  description?: string;
  route?: string;
}

interface CommandSearchProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function formatTitle(path: string): string {
  const segments = path.split("/").filter(Boolean);
  const lastSegment = segments[segments.length - 1] || "home";
  return lastSegment
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** True when the path contains a dynamic segment such as ":id". */
function hasDynamicSegment(path: string): boolean {
  return path.split("/").some((seg) => seg.startsWith(":"));
}

/**
 * Join a parent path and a child route segment into a single absolute path,
 * always producing a leading "/" and collapsing any duplicate slashes. Handles
 * both relative segments ("transactions") and absolute ones ("/errors/x").
 */
function joinPaths(parentPath: string, path: string): string {
  const parts = [...parentPath.split("/"), ...path.split("/")].filter(Boolean);
  return "/" + parts.join("/");
}

/**
 * Build the "App Pages" search items from the route tree. A page appears only
 * when:
 * - it is explicitly marked `searchable: true` (the default is excluded),
 * - it is not the catch-all ("*") or a <Navigate> redirect, and
 * - its path has no dynamic segments (e.g. ":id").
 *
 * The label uses the route's `searchTitle` when provided, otherwise falls back
 * to a slug-derived title. It never uses the page component's name.
 */
function getSearchItemsFromRoutes(): SearchItem[] {
  const items: SearchItem[] = [];
  const visitedPaths = new Set<string>();

  function extractRoutes(route: RouteConfig, parentPath: string = "/") {
    const rawPath = route.path ?? "";
    const path = rawPath === "/" ? "" : rawPath;
    const fullPath = joinPaths(parentPath, path);

    const isNavigate = (route.element as any)?.type?.name === "Navigate";
    const isRoot = fullPath === "/" || fullPath === "";

    if (
      path !== "*" &&
      !isNavigate &&
      !isRoot &&
      route.searchable === true &&
      !hasDynamicSegment(fullPath) &&
      !visitedPaths.has(fullPath)
    ) {
      visitedPaths.add(fullPath);
      items.push({
        title: route.searchTitle || formatTitle(fullPath),
        url: fullPath,
        group: "App Pages",
      });
    }

    if (route.children) {
      route.children.forEach((child) => extractRoutes(child, fullPath));
    }
  }

  routes.forEach((route) => extractRoutes(route));
  return items;
}

/**
 * Reduce a table-qualified field expression (e.g. "`tabDocType`.`name`") to a
 * plain column name ("name").
 */
function normalizeKey(key: string): string {
  const parts = String(key).replace(/`/g, "").split(".");
  return parts[parts.length - 1] || key;
}

/**
 * Normalise the `frappe.desk.reportview.get` payload into an array of plain
 * row objects. Accepts both the compressed `{ keys, values }` shape and a raw
 * array of objects.
 */
function rowsFromReport(message: any): any[] {
  if (!message) return [];
  if (Array.isArray(message)) return message;
  if (Array.isArray(message.values)) {
    const keys = (message.keys || []).map((k: string) => normalizeKey(k));
    return message.values.map((row: any[]) =>
      keys.reduce(
        (acc: Record<string, any>, key: string, i: number) => {
          acc[key] = row[i];
          return acc;
        },
        {},
      ),
    );
  }
  return [];
}

export function CommandSearch({ open, onOpenChange }: CommandSearchProps) {
  const navigate = useNavigate();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listContainerRef = React.useRef<HTMLDivElement>(null);

  const [searchTerm, setSearchTerm] = React.useState("");
  const [selectedDocType, setSelectedDocType] = React.useState("All");
  const [focusedIndex, setFocusedIndex] = React.useState(0);
  const [collapsedGroups, setCollapsedGroups] = React.useState<Record<string, boolean>>({});
  const [limit, setLimit] = React.useState(100);
  const [start, setStart] = React.useState(0);
  const [allowedDocTypes, setAllowedDocTypes] = React.useState<string[]>([]);
  // When false (default), only App Pages + Doctypes are returned as one flat
  // list. When true, global search results and the doctype filter pills are
  // included too.
  const [advancedMode, setAdvancedMode] = React.useState(false);
  // Collapses the doctype filter pills bar in advanced mode (default collapsed).
  const [filtersCollapsed, setFiltersCollapsed] = React.useState(true);

  const queryTerm = searchTerm.trim().replace(/\s\s+/g, " ");
  const shouldSearch = queryTerm.length > 1;

  // Fetch allowed doctypes from Global Search Settings
  const { data: settingsData } = useFrappeGetCall(
    open ? "frappe.client.get" : (null as any),
    open
      ? { doctype: "Global Search Settings", name: "Global Search Settings" }
      : {},
    open ? "global-search-settings" : null,
  );

  React.useEffect(() => {
    if (settingsData?.message?.allowed_in_global_search) {
      const types = (settingsData.message.allowed_in_global_search as any[]).map(
        (item: any) => item.document_type,
      );
      setAllowedDocTypes(types);
    }
  }, [settingsData]);

  // Fetch global search results from Frappe
  const searchParams: Record<string, any> = {
    text: queryTerm,
    limit: limit,
    start: start,
  };
  if (selectedDocType !== "All") {
    searchParams.doctype = selectedDocType;
  }

  // Global search only runs in advanced mode; the simple mode limits itself to
  // App Pages + Doctypes.
  const { data: searchResponse, isValidating: isSearchingGlobal } = useFrappeGetCall(
    shouldSearch && advancedMode ? "frappe.utils.global_search.search" : (null as any),
    searchParams,
    shouldSearch && advancedMode
      ? `awesomebar-${selectedDocType}-${queryTerm}-${start}-${limit}`
      : null,
  );

  // Fetch matching doctypes for the "Doctypes" results group (List / New links).
  // The lookup runs against the DocType doctype, which only desk users can read,
  // so tenants never get these results (they would land on a forbidden page).
  const canBrowseDoctypes =
    APP_PAGES_ENABLED && getBootUser()?.user_type === "System User";

  const { call: fetchDocTypes, result: docTypeResponse, loading: loadingDocTypes } = useFrappePostCall(
    "frappe.desk.reportview.get",
  );

  React.useEffect(() => {
    if (!shouldSearch || !canBrowseDoctypes || typeof fetchDocTypes !== "function") return;
    fetchDocTypes({
      doctype: "DocType",
      fields: [
        "`tabDocType`.`name`",
        "`tabDocType`.`issingle`",
        "`tabDocType`.`istable`",
      ],
      filters: [
        ["DocType", "name", "like", `%${queryTerm}%`],
        ["DocType", "istable", "=", 0],
      ],
      order_by: "`tabDocType`.`name` asc",
      start: 0,
      page_length: 20,
    });
  }, [shouldSearch, queryTerm, fetchDocTypes, canBrowseDoctypes]);

  React.useEffect(() => {
    setStart(0);
  }, [searchTerm, selectedDocType, limit]);

  // Focus input when modal opens
  React.useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  // Reset when dialog closes
  React.useEffect(() => {
    if (!open) {
      setSearchTerm("");
      setSelectedDocType("All");
      setStart(0);
      setFocusedIndex(0);
      setAdvancedMode(false);
      setFiltersCollapsed(true);
    }
  }, [open]);

  // Build the filtered and grouped results
  const routeItems = React.useMemo(() => getSearchItemsFromRoutes(), []);

  const filteredRouteItems = React.useMemo(() => {
    if (!queryTerm) return routeItems;
    const lower = queryTerm.toLowerCase();
    return routeItems.filter(
      (item) =>
        item.title.toLowerCase().includes(lower) ||
        (item.url && item.url.toLowerCase().includes(lower)),
    );
  }, [routeItems, queryTerm]);

  // Build the "Doctypes" results group from the DocType lookup. Single doctypes
  // only surface their name (no List/New); regular doctypes get "New X" and
  // "X List" entries that link into the /app/:doctype routes.
  const docTypeItems = React.useMemo(() => {
    if (!canBrowseDoctypes) return [];
    const items: SearchItem[] = [];
    const seen = new Set<string>();
    for (const row of rowsFromReport(docTypeResponse?.message)) {
      const name = row.name;
      if (!name || seen.has(name)) continue;
      seen.add(name);
      const slug = doctypeToSlug(name);
      if (Number(row.issingle) === 1) {
        items.push({
          title: name,
          url: `/app/${slug}`,
          group: "Doctypes",
          description: "Single document",
        });
      } else {
        items.push({
          title: `New ${name}`,
          url: `/app/${slug}/new`,
          group: "Doctypes",
          description: `Create new ${name}`,
        });
        items.push({
          title: `${name} List`,
          url: `/app/${slug}`,
          group: "Doctypes",
          description: `Browse ${name} records`,
        });
      }
    }
    return items;
  }, [docTypeResponse]);

  // Simple (default) mode results: App Pages + Doctypes combined into a single
  // flat list with no grouping and no filter pills.
  const defaultResults = React.useMemo(() => {
    const items: SearchItem[] = [...filteredRouteItems];
    if (shouldSearch) items.push(...docTypeItems);
    return items;
  }, [filteredRouteItems, docTypeItems, shouldSearch]);

  const filteredOptions = React.useMemo(() => {
    const allItems: SearchItem[] = [];

    // Add matched route items (always show when not searching, filtered when searching)
    if (!shouldSearch) {
      // No search term - show all routes
      allItems.push(...routeItems);
    } else {
      // Has search term - show filtered routes + global results
      allItems.push(...filteredRouteItems);
      const globalResults = (searchResponse?.message as any[]) || [];
      for (const item of globalResults) {
        allItems.push({
          title: item.title || item.name,
          name: item.name,
          doctype: item.doctype,
          description: item.content?.replace(/\|\|\|/g, " • ") || "",
          route: item.route,
          group: item.doctype || "Other",
        });
      }
      allItems.push(...docTypeItems);
    }

    // Group by group name
    const grouped: Record<string, SearchItem[]> = {};
    for (const item of allItems) {
      const type = item.group;
      if (selectedDocType !== "All" && type !== selectedDocType) {
        continue;
      }
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(item);
    }

    // Sort groups: active filter first, then "App Pages", "Doctypes", the
    // advanced (global search) doctype groups alphabetically, and "Other" last.
    const sortedGroups = Object.keys(grouped).sort((a, b) => {
      if (a === selectedDocType) return -1;
      if (b === selectedDocType) return 1;
      if (a === "App Pages") return -1;
      if (b === "App Pages") return 1;
      if (a === "Doctypes") return -1;
      if (b === "Doctypes") return 1;
      if (a === "Other") return 1;
      if (b === "Other") return -1;
      return a.localeCompare(b);
    });

    const sorted: Record<string, SearchItem[]> = {};
    for (const key of sortedGroups) {
      sorted[key] = grouped[key];
    }
    return sorted;
  }, [shouldSearch, routeItems, filteredRouteItems, docTypeItems, searchResponse, selectedDocType]);

  // Flatten all visible (non-collapsed) items for keyboard navigation
  const flattenedOptions = React.useMemo(() => {
    return Object.entries(filteredOptions)
      .filter(([docType]) => !collapsedGroups[docType])
      .flatMap(([, items]) => items);
  }, [filteredOptions, collapsedGroups]);

  const hasResults = Object.keys(filteredOptions).length > 0;

  // Items the keyboard can navigate over: the flat default list in simple mode,
  // or the flattened grouped list in advanced mode.
  const keyboardOptions = advancedMode ? flattenedOptions : defaultResults;

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onOpenChange(false);
      return;
    }

    if (keyboardOptions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusedIndex((prev) => (prev + 1) % keyboardOptions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedIndex(
        (prev) =>
          (prev - 1 + keyboardOptions.length) % keyboardOptions.length,
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (keyboardOptions[focusedIndex]) {
        handleSelectOption(keyboardOptions[focusedIndex]);
      }
    }
  };

  // Auto-scroll focused item into view
  React.useEffect(() => {
    if (listContainerRef.current) {
      const activeElement = listContainerRef.current.querySelector(
        "[data-active='true']",
      );
      if (activeElement) {
        activeElement.scrollIntoView({ block: "nearest" });
      }
    }
  }, [focusedIndex]);

  function doctypeToUrl(dt: string): string {
    return dt
      .replace(/([A-Z])/g, " $1")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "-");
  }

  const handleSelectOption = (option: SearchItem) => {
    if (option.url) {
      navigate(option.url);
    } else if (option.route) {
      navigate(option.route);
    } else if (option.doctype && option.name) {
      navigate(`/app/${doctypeToUrl(option.doctype)}/${option.name}`);
    }
    onOpenChange(false);
  };

  const toggleGroupCollapse = (group: string) => {
    setCollapsedGroups((prev) => ({
      ...prev,
      [group]: !prev[group],
    }));
  };

  // Compute which doctype filter pills to show
  const reorderedDocTypes = React.useMemo(() => {
    return [...allowedDocTypes].sort((a, b) => {
      const aHasResults = filteredOptions[a] !== undefined;
      const bHasResults = filteredOptions[b] !== undefined;
      if (aHasResults && !bHasResults) return -1;
      if (!aHasResults && bHasResults) return 1;
      return 0;
    });
  }, [allowedDocTypes, filteredOptions]);

  // Combined loading state for the global search and the doctype lookup.
  const isSearching = isSearchingGlobal || loadingDocTypes;

  if (!open) return null;

  let globalItemIndex = 0;

  // Reusable single result row used by both the simple flat list and the
  // grouped advanced list. `currentIndex` is its position in the visible list,
  // used for keyboard focus highlighting.
  const renderItem = (option: SearchItem, currentIndex: number) => {
    const isFocused = currentIndex === focusedIndex;
    return (
      <div
        key={`${option.group}-${option.title}-${option.name || currentIndex}`}
        data-active={isFocused}
        className={`flex items-center justify-between gap-x-4 px-3 py-2 rounded-lg cursor-pointer transition-all duration-150 text-left ${
          isFocused
            ? "bg-primary text-primary-foreground"
            : "hover:bg-accent hover:text-accent-foreground"
        }`}
        onClick={() => handleSelectOption(option)}
        onMouseEnter={() => setFocusedIndex(currentIndex)}
      >
        <div className="flex items-center gap-x-4 min-w-0 grow">
          {option.url ? (
            <FileSearch
              className={`w-4 h-4 shrink-0 transition-colors ${
                isFocused ? "text-primary-foreground" : "text-muted-foreground"
              }`}
            />
          ) : (
            <FolderOpen
              className={`w-4 h-4 shrink-0 transition-colors ${
                isFocused ? "text-primary-foreground" : "text-muted-foreground"
              }`}
            />
          )}
          <div className="flex flex-col min-w-0">
            <span
              className={`text-sm font-semibold truncate ${
                isFocused
                  ? "text-primary-foreground"
                  : "text-foreground"
              }`}
            >
              {option.title}
            </span>
            {option.description && (
              <span
                className={`text-xs truncate mt-0.5 max-w-xl ${
                  isFocused
                    ? "text-primary-foreground/80"
                    : "text-muted-foreground"
                }`}
              >
                {option.description}
              </span>
            )}
          </div>
        </div>
        {option.name && (
          <span
            className={`text-[11px] font-mono px-2 py-0.5 rounded shrink-0 transition-colors ${
              isFocused
                ? "bg-primary-foreground/20 text-primary-foreground"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {option.name}
          </span>
        )}
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] flex items-start justify-center pt-[5vh]"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="bg-popover w-full max-w-7xl rounded-2xl shadow-2xl border border-border overflow-hidden mx-4 flex flex-col h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="flex items-center justify-between gap-x-3 px-4 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-x-3 grow">
            <Search className="text-primary w-5 h-5 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              className="w-full text-lg text-foreground placeholder:text-muted-foreground focus:outline-none bg-transparent"
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setFocusedIndex(0);
              }}
              onKeyDown={handleKeyDown}
            />
          </div>
          <button
            onClick={() => setAdvancedMode((v) => !v)}
            title={
              advancedMode
                ? "Switch back to simple search"
                : "Include global search results and doctype filters"
            }
            className={`flex items-center gap-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors shrink-0 ${
              advancedMode
                ? "bg-primary text-primary-foreground border-primary shadow-sm"
                : "bg-card text-muted-foreground border-border hover:bg-accent hover:text-accent-foreground"
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            {advancedMode ? "Simple" : "Advanced"}
          </button>
          <button
            onClick={() => onOpenChange(false)}
            className="text-muted-foreground hover:text-foreground p-1 rounded-lg transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* DocType Filter Pills (advanced mode only, collapsible) */}
        {advancedMode && reorderedDocTypes.length > 0 && (
          <div className="border-b border-border shrink-0">
            <button
              onClick={() => setFiltersCollapsed((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-2 text-xs font-bold uppercase tracking-wider text-primary hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer"
            >
              <span className="flex items-center gap-x-2">
                <Tags className="w-3.5 h-3.5 opacity-70" />
                Filters
                <span className="bg-primary/10 text-primary rounded-full px-2 py-0.5 text-[10px] normal-case font-bold">
                  {selectedDocType === "All"
                    ? `${reorderedDocTypes.length} doctypes`
                    : selectedDocType}
                </span>
              </span>
              {filtersCollapsed ? (
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              ) : (
                <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" />
              )}
            </button>
            {!filtersCollapsed && (
              <div className="flex flex-wrap items-center gap-2 px-3 pb-3 bg-muted">
                <button
                  onClick={() => setSelectedDocType("All")}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-full transition-all shrink-0 ${
                    selectedDocType === "All"
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground border border-border"
                  }`}
                >
                  All Results
                </button>
                {reorderedDocTypes.map((type) => {
                  const isSelected = selectedDocType === type;
                  const hasMatches = filteredOptions[type] !== undefined;
                  return (
                    <button
                      key={type}
                      onClick={() => setSelectedDocType(type)}
                      className={`px-4 py-1.5 text-xs font-semibold rounded-full transition-all shrink-0 relative ${
                        isSelected
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : hasMatches
                            ? "bg-primary/10 text-primary border border-primary/30 shadow-sm font-bold ring-2 ring-primary/20"
                            : "bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground border border-border"
                      }`}
                    >
                      {type}
                      {hasMatches && !isSelected && (
                        <span className="absolute -top-1 -right-1 w-2 h-2 bg-primary rounded-full" />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Results Area */}
        <div
          ref={listContainerRef}
          className="overflow-y-auto px-4 py-3 bg-muted/40 grow scroll-smooth"
        >
          {advancedMode ? (
            shouldSearch ? (
              hasResults ? (
              <div className="flex flex-col gap-y-6 max-w-none">
                {Object.entries(filteredOptions).map(([group, items]) => {
                  const isCollapsed = collapsedGroups[group];
                  const isTargetGroup = group === selectedDocType;

                  return (
                    <div
                      key={group}
                      className={`flex flex-col gap-y-1.5 ${
                        isTargetGroup
                          ? "border-2 border-primary/20 p-4 rounded-2xl bg-primary/5 shadow-sm"
                          : ""
                      }`}
                    >
                      {/* Group Header (clickable to collapse/expand) */}
                      <div
                        onClick={() => toggleGroupCollapse(group)}
                        className="flex items-center justify-between px-1 text-xs font-bold text-primary uppercase tracking-wider cursor-pointer select-none group"
                      >
                        <div className="flex items-center gap-x-2">
                          <Tags className="w-3 h-3 opacity-70" />
                          <span
                            className={
                              isTargetGroup
                                ? "text-sm text-primary font-extrabold"
                                : ""
                            }
                          >
                            {group}{" "}
                            {isTargetGroup && selectedDocType !== "All" && (
                              <span className="text-xs font-normal normal-case text-muted-foreground">
                                (Active Filter)
                              </span>
                            )}
                          </span>
                          <span className="bg-primary/10 text-primary rounded-full px-2 py-0.5 text-[10px] normal-case font-bold">
                            {items.length}
                          </span>
                        </div>
                        {isCollapsed ? (
                          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                        ) : (
                          <ChevronUp className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                        )}
                      </div>

                      {!isCollapsed && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 bg-card border border-border rounded-xl p-1.5 shadow-sm w-full">
                          {items.map((option) => {
                            const currentIndex = globalItemIndex++;
                            return renderItem(option, currentIndex);
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : isSearching ? (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-border border-t-primary rounded-full animate-spin" />
                  Searching...
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                No matches found for "{searchTerm}" under the selected scope.
              </div>
            )
          ) : (
            <div className="flex flex-col gap-y-6 max-w-none">
              {Object.entries(filteredOptions).map(([group, items]) => {
                const isCollapsed = collapsedGroups[group];

                return (
                  <div key={group} className="flex flex-col gap-y-1.5">
                    {/* Group Header */}
                    <div
                      onClick={() => toggleGroupCollapse(group)}
                      className="flex items-center justify-between px-1 text-xs font-bold text-primary uppercase tracking-wider cursor-pointer select-none group"
                    >
                      <div className="flex items-center gap-x-2">
                        <Tags className="w-3 h-3 opacity-70" />
                        <span>{group}</span>
                        <span className="bg-primary/10 text-primary rounded-full px-2 py-0.5 text-[10px] normal-case font-bold">
                          {items.length}
                        </span>
                      </div>
                      {isCollapsed ? (
                        <ChevronDown className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                      ) : (
                        <ChevronUp className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                      )}
                    </div>

                    {!isCollapsed && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 bg-card border border-border rounded-xl p-1.5 shadow-sm w-full">
                        {items.map((option) => {
                          const currentIndex = globalItemIndex++;
                          return renderItem(option, currentIndex);
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            )
          )
          : (
            shouldSearch ? (
              defaultResults.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                  {defaultResults.map((option, index) =>
                    renderItem(option, index),
                  )}
                </div>
              ) : isSearching ? (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-border border-t-primary rounded-full animate-spin" />
                    Searching...
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  No matches found for "{searchTerm}".
                </div>
              )
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                {defaultResults.map((option, index) =>
                  renderItem(option, index),
                )}
              </div>
            )
          )}
        </div>

        {/* Footer: Navigation tips, Per Page, Pagination */}
        <div className="bg-muted px-4 py-2 border-t border-border text-xs text-muted-foreground flex flex-col sm:flex-row items-center justify-between gap-4 shrink-0">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div className="flex items-center gap-x-2 text-[11px] text-muted-foreground">
              <span>↑↓ to navigate</span>
              <span>•</span>
              <span>↵ to select</span>
              <span>•</span>
              <span>Esc to close</span>
            </div>

            {advancedMode && shouldSearch && (
              <div className="flex items-center gap-x-2 border-l border-border pl-4">
                <span className="text-[11px] font-medium text-muted-foreground">
                  Per Page:
                </span>
                <select
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="bg-card border border-border rounded px-1.5 py-0.5 text-xs text-muted-foreground focus:outline-none focus:border-primary font-medium shadow-sm"
                >
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={500}>500</option>
                  <option value={1000}>1000</option>
                  <option value={2500}>2500</option>
                </select>
              </div>
            )}
          </div>

          {advancedMode && shouldSearch &&
            ((searchResponse?.message as any[])?.length > 0 || start > 0) && (
              <div className="flex items-center gap-x-3">
                <button
                  disabled={start === 0}
                  onClick={() =>
                    setStart((prev) => Math.max(0, prev - limit))
                  }
                  className="flex items-center gap-x-1 px-3 py-1 text-xs font-medium rounded-lg border border-border bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:hover:bg-card transition-all shadow-sm"
                >
                  <ChevronDown className="w-3 h-3 rotate-90" />
                  <span>Prev</span>
                </button>
                <span className="text-xs font-medium text-muted-foreground">
                  Showing results {start + 1} –{" "}
                  {start + ((searchResponse?.message as any[])?.length || 0)}
                </span>
                <button
                  disabled={
                    !searchResponse?.message ||
                    (searchResponse.message as any[]).length < limit
                  }
                  onClick={() => setStart((prev) => prev + limit)}
                  className="flex items-center gap-x-1 px-3 py-1 text-xs font-medium rounded-lg border border-border bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-50 disabled:hover:bg-card transition-all shadow-sm"
                >
                  <span>Next</span>
                  <ChevronDown className="w-3 h-3 -rotate-90" />
                </button>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}

export function SearchTrigger({ onClick }: { onClick: () => void }) {
  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onClick();
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [onClick]);

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-8 px-3 py-1 relative w-full justify-start text-muted-foreground sm:pr-12 md:w-36 lg:w-56"
    >
      <Search className="mr-2 h-3.5 w-3.5" />
      <span className="hidden lg:inline-flex">Search ...</span>
      <span className="inline-flex lg:hidden">Search...</span>
      <kbd className="pointer-events-none absolute right-1.5 top-1.5 hidden h-4 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
        <span className="text-xs">⌘</span>K
      </kbd>
    </button>
  );
}