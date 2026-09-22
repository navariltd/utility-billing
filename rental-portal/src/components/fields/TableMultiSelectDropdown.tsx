/**
 * TableMultiSelectDropdown – the dropdown overlay for TableMultiSelect with search and option list.
 *
 * Key dependencies: rendered via portal, handles infinite scroll and keyboard navigation.
 */

import { Search, Loader2, Check } from "lucide-react";
import * as React from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";
import type { DropdownOption } from "./table-multi-select-types";

interface TableMultiSelectDropdownProps {
  /** Whether the dropdown is open. */
  isOpen: boolean;
  /** Whether the component is disabled. */
  isDisabled: boolean;
  /** Whether a link field exists. */
  hasLinkField: boolean;
  /** Options to display. */
  options: DropdownOption[];
  /** Currently selected values. */
  value: string[];
  /** The search input value. */
  search: string;
  /** Whether results are loading. */
  loading: boolean;
  /** The link doctype for the placeholder. */
  linkDoctype: string;
  /** The dropdown position. */
  dropdownPosition: "top" | "bottom";
  /** The button ref for positioning. */
  buttonRef: React.RefObject<HTMLDivElement | null>;
  /** The input ref. */
  inputRef: React.RefObject<HTMLInputElement | null>;
  /** The dropdown ref. */
  dropdownRef: React.RefObject<HTMLDivElement | null>;
  /** Index of the highlighted option. */
  highlightedIndex: number;
  /** The doctype metadata (for subtitle info). */
  docMeta: any;
  /** Selection handler. */
  onSelect: (opt: DropdownOption) => void;
  /** Input change handler. */
  onInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Key down handler. */
  onKeyDown: (e: React.KeyboardEvent) => void;
  /** Scroll handler for infinite scroll. */
  onScroll: (e: React.UIEvent<HTMLDivElement>) => void;
}

/** Build subtitle lines for an option. */
function getSubtitles(opt: DropdownOption, docMeta: any): string[] {
  const subtitles: string[] = [];

  if (docMeta) {
    const titleField = docMeta.show_title_field_in_link ? docMeta.title_field : null;
    if (titleField && opt.value !== opt.label) {
      subtitles.push(opt.value);
    }
  }

  if (opt.description) {
    subtitles.push(opt.description);
  }

  if (opt.extra && typeof opt.extra === "string") {
    subtitles.push(opt.extra);
  }

  return subtitles;
}

/** The dropdown overlay rendered via portal. */
export const TableMultiSelectDropdown: React.FC<TableMultiSelectDropdownProps> = ({
  isOpen,
  isDisabled,
  hasLinkField,
  options,
  value,
  search,
  loading,
  linkDoctype,
  dropdownPosition,
  buttonRef,
  inputRef,
  dropdownRef,
  highlightedIndex,
  docMeta,
  onSelect,
  onInputChange,
  onKeyDown,
  onScroll,
}) => {
  if (!isOpen || isDisabled || !hasLinkField) return null;

  const bottom = buttonRef.current
    ? window.innerHeight - buttonRef.current.getBoundingClientRect().top + 4
    : undefined;

  return createPortal(
    <div
      ref={dropdownRef}
      style={{
        position: "fixed",
        top:
          dropdownPosition === "bottom" && buttonRef.current
            ? buttonRef.current.getBoundingClientRect().bottom + 4
            : undefined,
        bottom: dropdownPosition === "top" ? bottom : undefined,
        left: buttonRef.current ? buttonRef.current.getBoundingClientRect().left : 0,
        width: buttonRef.current ? buttonRef.current.getBoundingClientRect().width : 300,
        zIndex: 999999,
      }}
      className="bg-popover border border-input text-popover-foreground rounded-md shadow-md overflow-hidden animate-in fade-in-0 zoom-in-95 duration-100"
    >
      <div className="p-1 border-b border-border">
        <div className="relative flex items-center">
          <Search className="absolute left-2.5 size-4 opacity-50" />
          <input
            ref={inputRef}
            value={search}
            onChange={onInputChange}
            onKeyDown={onKeyDown}
            className="w-full bg-transparent pl-8 pr-8 py-1.5 text-sm rounded-sm outline-none placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring"
            placeholder={`Search ${linkDoctype}...`}
          />
          {loading && (
            <Loader2 className="absolute right-2.5 size-4 animate-spin opacity-50" />
          )}
        </div>
      </div>
      <div className="max-h-60 overflow-y-auto p-1" onScroll={onScroll}>
        {loading && options.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            Searching...
          </div>
        ) : options.length > 0 ? (
          options.map((opt, idx) => {
            const subtitles = getSubtitles(opt, docMeta);
            const isSelected = value.includes(opt.value);
            return (
              <div
                key={`${opt.value}-${idx}`}
                onMouseDown={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onSelect(opt);
                }}
                onMouseEnter={() => {
                  // Highlight set via parent handler
                }}
                className={cn(
                  "relative flex w-full cursor-default items-center rounded-sm px-2 py-1.5 text-sm outline-none select-none transition-colors justify-between",
                  highlightedIndex === idx
                    ? "bg-accent text-accent-foreground"
                    : "",
                  isSelected ? "bg-accent/50" : "",
                )}
              >
                <div className="flex flex-col min-w-0 w-full py-0.5">
                  <span className="font-medium text-foreground truncate">
                    {opt.label}
                  </span>
                  {subtitles.length > 0 && (
                    <span className="text-xs text-muted-foreground truncate max-w-full flex items-center gap-1.5 mt-0.5">
                      {subtitles.join(" • ")}
                    </span>
                  )}
                </div>
                {isSelected && (
                  <Check className="size-4 text-primary shrink-0 ml-2" />
                )}
              </div>
            );
          })
        ) : (
          <div className="py-6 text-center text-sm text-muted-foreground">
            No results found
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
};

export default TableMultiSelectDropdown;