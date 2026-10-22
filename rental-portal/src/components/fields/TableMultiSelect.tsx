/**
 * TableMultiSelect – multi-select dropdown for Frappe Link fields.
 *
 * Key dependencies: uses frappe-service for API calls, renders via TableMultiSelectDropdown.
 * Fetches doctype metadata to find the first Link field, then searches link doctype values.
 */

"use client";

import { ChevronDown, X, AlertTriangle } from "lucide-react";
import * as React from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { useCallPost } from "@/lib/frappe-service";
import { cn } from "@/lib/utils";
import { TableMultiSelectDropdown } from "./TableMultiSelectDropdown";
import { useTableMultiSelectMeta } from "./use-table-multi-select-meta";
import { useTableMultiSelectSearch } from "./use-table-multi-select-search";
import type { DropdownOption, TableMultiSelectProps } from "./table-multi-select-types";

export const TableMultiSelect = ({
  doctype,
  value = [],
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  placeholder = "Select options...",
  linkFieldname,
  filters = {},
  query,
  debounceDelay = 300,
  pageLength = 20,
}: TableMultiSelectProps) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [selectedDisplayValues, setSelectedDisplayValues] = React.useState<{ label: string; value: string }[]>([]);
  const [dropdownPosition, setDropdownPosition] = React.useState<"top" | "bottom">("bottom");

  const containerRef = React.useRef<HTMLDivElement>(null);
  const buttonRef = React.useRef<HTMLDivElement>(null);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  const { post: searchLink } = useCallPost("frappe.desk.search.search_link");
  const {
    docMeta, linkDoctype, metaLoading, errorMessage,
  } = useTableMultiSelectMeta(doctype, linkFieldname, filters);

  const {
    options, loading, highlightedIndex, search,
    isSelectingRef, hasFetchedOnceRef, performSearch,
    setOptions: _setOptions, setSearch, setLoading: _setLoading, setHighlightedIndex,
    lastSearchedTxtRef, inputRef,
  } = useTableMultiSelectSearch(linkDoctype, doctype, query, filters, debounceDelay, pageLength);

  // Load display labels for selected values
  React.useEffect(() => {
    const fetchLabels = async () => {
      if (!linkDoctype || value.length === 0 || selectedDisplayValues.length > 0) return;
      try {
        const response = await searchLink({
          txt: "", doctype: linkDoctype, page_length: value.length,
          filters: JSON.stringify({ name: ["in", value] }),
        });
        const results: DropdownOption[] = ((response as any)?.message || []).map((opt: any) => ({
          label: opt.label || opt.value, value: opt.value, description: opt.description || "",
        }));
        setSelectedDisplayValues(value.map((v) => {
          const found = results.find((r) => r.value === v);
          return { label: found?.label || v, value: v };
        }));
      } catch {
        setSelectedDisplayValues(value.map((v) => ({ label: v, value: v })));
      }
    };
    fetchLabels();
  }, [linkDoctype, value, searchLink]);

  const handleOpen = React.useCallback(() => {
    if (disabled || !linkDoctype || metaLoading || isSelectingRef.current) return;
    const nextOpen = !isOpen;
    setIsOpen(nextOpen);
    if (nextOpen && !hasFetchedOnceRef.current) {
      hasFetchedOnceRef.current = true;
      lastSearchedTxtRef.current = "";
      performSearch("", pageLength);
    }
  }, [disabled, linkDoctype, metaLoading, isOpen, performSearch, pageLength, isSelectingRef, hasFetchedOnceRef, lastSearchedTxtRef]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setSearch(val);
    if (val !== lastSearchedTxtRef.current) performSearch(val, pageLength);
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    if (target.scrollHeight - target.scrollTop <= target.clientHeight + 15) {
      if (options.length >= pageLength) performSearch(search, options.length + pageLength, true);
    }
  };

  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node) &&
          dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearch("");
        lastSearchedTxtRef.current = null;
        setHighlightedIndex(-1);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  React.useEffect(() => {
    if (isOpen && inputRef.current && !isSelectingRef.current) {
      inputRef.current.focus();
      if (buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        setDropdownPosition(window.innerHeight - rect.bottom < 320 && rect.top > window.innerHeight - rect.bottom ? "top" : "bottom");
      }
    }
  }, [isOpen]);

  const handleSelect = React.useCallback((opt: DropdownOption) => {
    isSelectingRef.current = true;
    const newValue = value.includes(opt.value) ? value.filter((v) => v !== opt.value) : [...value, opt.value];
    const newDisplay = value.includes(opt.value)
      ? selectedDisplayValues.filter((v) => v.value !== opt.value)
      : [...selectedDisplayValues, { label: opt.label, value: opt.value }];
    onChange(newValue);
    setSelectedDisplayValues(newDisplay);
    setSearch("");
    lastSearchedTxtRef.current = null;
    setHighlightedIndex(-1);
    setTimeout(() => { isSelectingRef.current = false; inputRef.current?.focus(); }, 200);
  }, [value, onChange, selectedDisplayValues]);

  const handleRemove = React.useCallback((optionValue: string) => {
    onChange(value.filter((v) => v !== optionValue));
    setSelectedDisplayValues(selectedDisplayValues.filter((v) => v.value !== optionValue));
  }, [value, onChange, selectedDisplayValues]);

  const handleKeyDown = React.useCallback((e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "Enter") { e.preventDefault(); handleOpen(); }
      return;
    }
    switch (e.key) {
      case "ArrowDown": e.preventDefault(); setHighlightedIndex((p) => (p < options.length - 1 ? p + 1 : p)); break;
      case "ArrowUp": e.preventDefault(); setHighlightedIndex((p) => (p > 0 ? p - 1 : -1)); break;
      case "Enter": e.preventDefault(); if (highlightedIndex >= 0 && options[highlightedIndex]) handleSelect(options[highlightedIndex]); break;
      case "Escape": setIsOpen(false); setSearch(""); lastSearchedTxtRef.current = null; setHighlightedIndex(-1); break;
    }
  }, [isOpen, options, highlightedIndex, handleSelect, handleOpen]);

  const hasLinkField = !!linkDoctype;
  const isDisabled = disabled || !hasLinkField || metaLoading;

  return (
    <div ref={containerRef}
      onBlur={(e) => { if (!containerRef.current?.contains(e.relatedTarget as Node) && !isSelectingRef.current) onBlur?.(); }}
      className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <label className="text-sm font-medium text-foreground flex items-center gap-0.5 select-none">
          {label}
          {required && <span className="text-destructive font-bold text-red-500 ml-0.5">*</span>}
        </label>
      )}
      {errorMessage && (
        <div className="flex items-center gap-2 p-2 rounded-md bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
          <AlertTriangle className="size-4 text-amber-600 dark:text-amber-400 shrink-0" />
          <span className="text-xs text-amber-700 dark:text-amber-300">{errorMessage}</span>
        </div>
      )}
      <div className="relative">
        <div ref={buttonRef} onClick={handleOpen}
          className={cn("flex min-h-9 w-full flex-wrap items-center gap-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors outline-none cursor-pointer",
            isDisabled && "opacity-50 cursor-not-allowed", isOpen && "ring-[3px] ring-ring/50 border-ring")}>
          {metaLoading ? (
            <div className="flex items-center gap-2 w-full"><Skeleton className="h-3.5 w-3.5 rounded" /><Skeleton className="h-3.5 w-28" /></div>
          ) : selectedDisplayValues.length === 0 ? (
            <span className="text-muted-foreground">{placeholder}</span>
          ) : selectedDisplayValues.map((opt) => (
            <span key={opt.value} className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs max-w-[200px]">
              <span className="truncate">{opt.label}</span>
              {!isDisabled && (
                <button type="button" onClick={(e) => { e.stopPropagation(); handleRemove(opt.value); }} className="hover:text-destructive shrink-0">
                  <X className="size-3" />
                </button>
              )}
            </span>
          ))}
          <ChevronDown className={cn("ml-auto size-4 opacity-50 transition-transform duration-200 shrink-0", isOpen && "rotate-180")} />
        </div>
        <TableMultiSelectDropdown
          isOpen={isOpen} isDisabled={isDisabled} hasLinkField={hasLinkField}
          options={options} value={value} search={search} loading={loading}
          linkDoctype={linkDoctype} dropdownPosition={dropdownPosition}
          buttonRef={buttonRef} inputRef={inputRef} dropdownRef={dropdownRef}
          highlightedIndex={highlightedIndex} docMeta={docMeta}
          onSelect={handleSelect} onInputChange={handleInputChange}
          onKeyDown={handleKeyDown} onScroll={handleScroll} />
      </div>
    </div>
  );
};

export default TableMultiSelect;