"use client";

import { useCallPost } from "@/lib/frappe-service";
import { cn } from "@/lib/utils";
import { Check, ChevronDown, Loader2, Search, X } from "lucide-react";
import * as React from "react";
import { createPortal } from "react-dom";

export interface DropdownOption {
  label: string;
  value: string;
  extra?: any;
  description?: string;
  avatar?: string;
  icon?: React.ReactNode;
  metadata?: Record<string, any>;
}

interface LinkFieldProps {
  doctype: string;
  value: string;
  onChange: (val: string, option?: DropdownOption) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  clearable?: boolean;
  referenceDoctype?: string;
  linkFieldname?: string;
  query?: string;
  filters?: Record<string, any>;
  debounceDelay?: number;
  pageLength?: number;
  required?: boolean;
  label?: string;
}

export const LinkField = ({
  doctype,
  value,
  onChange,
  onBlur,
  placeholder,
  className = "",
  disabled = false,
  clearable = true,
  referenceDoctype,
  linkFieldname,
  query,
  filters = {},
  debounceDelay = 300,
  pageLength = 10,
  required = false,
  label,
}: LinkFieldProps) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const [options, setOptions] = React.useState<DropdownOption[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [dropdownPosition, setDropdownPosition] = React.useState<
    "top" | "bottom"
  >("bottom");
  const [highlightedIndex, setHighlightedIndex] = React.useState(-1);
  const [docMeta, setDocMeta] = React.useState<any>(null);
  const [hasLoadedMeta, setHasLoadedMeta] = React.useState(false);

  const containerRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const buttonRef = React.useRef<HTMLDivElement>(null);
  const dropdownRef = React.useRef<HTMLDivElement>(null);
  const searchTimeoutRef = React.useRef<any>(null);
  const isSelectingRef = React.useRef(false);
  const hasFetchedOnceRef = React.useRef(false);
  const lastSearchedTxtRef = React.useRef<string | null>(null);
  const activeRequestIdRef = React.useRef<number>(0);
  const currentPageLengthRef = React.useRef<number>(pageLength);
  const hasMoreRef = React.useRef<boolean>(true);
  const isFetchingMoreRef = React.useRef<boolean>(false);

  const { post: fetchDocType } = useCallPost("frappe.desk.form.load.getdoctype");
  const { post: searchLink } = useCallPost("frappe.desk.search.search_link");

  const prevFiltersRef = React.useRef(filters);

  React.useEffect(() => {
    if (JSON.stringify(prevFiltersRef.current) !== JSON.stringify(filters)) {
      hasFetchedOnceRef.current = false;
      lastSearchedTxtRef.current = null;
      setOptions([]);
      prevFiltersRef.current = filters;
    }
  }, [filters]);

  const performSearch = React.useCallback(
    async (searchTerm: string, limit: number, append = false) => {
      if (!doctype) return;
      if (searchTimeoutRef.current && !append) {
        clearTimeout(searchTimeoutRef.current);
      }

      if (append) {
        if (isFetchingMoreRef.current || !hasMoreRef.current) return;
        isFetchingMoreRef.current = true;
      } else {
        activeRequestIdRef.current += 1;
        setLoading(true);
        hasMoreRef.current = true;
      }

      const currentRequestId = activeRequestIdRef.current;

      const executeFetch = async () => {
        try {
          if (currentRequestId !== activeRequestIdRef.current) return;

          const response = await searchLink({
            txt: searchTerm,
            doctype: doctype,
            reference_doctype: referenceDoctype,
            page_length: limit,
            link_fieldname: linkFieldname,
            query: query,
            filters: JSON.stringify(filters),
          });

          if (currentRequestId !== activeRequestIdRef.current) return;

          const message = (response as any)?.message || [];
          const results = message.map((opt: any) => ({
            label: opt.label || opt.value,
            value: opt.value,
            description: opt.description || "",
            extra: opt.extra,
          }));

          if (results.length < limit) {
            hasMoreRef.current = false;
          } else {
            hasMoreRef.current = true;
          }

          if (!isSelectingRef.current) {
            if (append) {
              setOptions((prev) => {
                const existingValues = new Set(prev.map((o) => o.value));
                const filteredNew = results.filter(
                  (o: any) => !existingValues.has(o.value),
                );
                return [...prev, ...filteredNew];
              });
            } else {
              setOptions(results);
              lastSearchedTxtRef.current = searchTerm;
            }
          }
        } catch (error) {
          if (currentRequestId === activeRequestIdRef.current) {
            console.error(error);
          }
        } finally {
          if (currentRequestId === activeRequestIdRef.current) {
            if (append) {
              isFetchingMoreRef.current = false;
            } else {
              setLoading(false);
            }
          }
        }
      };

      if (append) {
        executeFetch();
      } else {
        searchTimeoutRef.current = setTimeout(executeFetch, debounceDelay);
      }
    },
    [
      doctype,
      referenceDoctype,
      linkFieldname,
      query,
      filters,
      debounceDelay,
      searchLink,
    ],
  );

  const loadMeta = React.useCallback(async () => {
    if (!doctype || hasLoadedMeta) return;

    try {
      const response = await fetchDocType({
        doctype: doctype,
        with_parent: 1,
      });
      if (response && (response as any).docs) {
        setDocMeta((response as any).docs[0]);
      }
      setHasLoadedMeta(true);
    } catch (error) {
      console.error(error);
    }
  }, [doctype, hasLoadedMeta, fetchDocType]);

  const handleOpen = React.useCallback(() => {
    if (disabled || isSelectingRef.current) return;

    const nextOpen = !isOpen;
    setIsOpen(nextOpen);

    if (nextOpen) {
      loadMeta();

      if (!hasFetchedOnceRef.current) {
        hasFetchedOnceRef.current = true;
        lastSearchedTxtRef.current = "";
        currentPageLengthRef.current = pageLength;
        performSearch("", pageLength);
      }
    }
  }, [disabled, isOpen, loadMeta, performSearch, pageLength]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setSearch(val);

    if (val !== lastSearchedTxtRef.current) {
      currentPageLengthRef.current = pageLength;
      performSearch(val, pageLength);
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    if (target.scrollHeight - target.scrollTop <= target.clientHeight + 15) {
      if (
        options.length >= pageLength &&
        hasMoreRef.current &&
        !isFetchingMoreRef.current
      ) {
        currentPageLengthRef.current += pageLength;
        performSearch(search, currentPageLengthRef.current, true);
      }
    }
  };

  React.useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        if (
          dropdownRef.current &&
          !dropdownRef.current.contains(e.target as Node)
        ) {
          setIsOpen(false);
          setSearch("");
          lastSearchedTxtRef.current = null;
          setHighlightedIndex(-1);
        }
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
        if (
          window.innerHeight - rect.bottom < 320 &&
          rect.top > window.innerHeight - rect.bottom
        ) {
          setDropdownPosition("top");
        } else {
          setDropdownPosition("bottom");
        }
      }
    }
  }, [isOpen]);

  const handleSelect = React.useCallback(
    (opt: DropdownOption) => {
      isSelectingRef.current = true;
      onChange(opt.value, opt);
      setIsOpen(false);
      setSearch("");
      lastSearchedTxtRef.current = null;
      setHighlightedIndex(-1);
      setTimeout(() => {
        isSelectingRef.current = false;
      }, 200);
    },
    [onChange],
  );

  const handleClear = React.useCallback(() => {
    isSelectingRef.current = true;
    onChange("", undefined);
    setSearch("");
    lastSearchedTxtRef.current = null;
    setIsOpen(false);
    setTimeout(() => {
      isSelectingRef.current = false;
    }, 200);
  }, [onChange]);

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) {
        if (e.key === "ArrowDown" || e.key === "Enter") {
          e.preventDefault();
          handleOpen();
        }
        return;
      }
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < options.length - 1 ? prev + 1 : prev,
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
          break;
        case "Enter":
          e.preventDefault();
          if (highlightedIndex >= 0 && options[highlightedIndex]) {
            handleSelect(options[highlightedIndex]);
          }
          break;
        case "Escape":
          setIsOpen(false);
          setSearch("");
          lastSearchedTxtRef.current = null;
          setHighlightedIndex(-1);
          break;
      }
    },
    [isOpen, options, highlightedIndex, handleSelect, handleOpen],
  );

  const getSubtitles = (opt: DropdownOption) => {
    const subtitles: string[] = [];

    if (docMeta) {
      const titleField = docMeta.show_title_field_in_link
        ? docMeta.title_field
        : null;
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
  };

  const selectedOption = value ? { label: value, value } : null;
  const displayLabel = label;

  const dropdown =
    isOpen && !disabled && doctype ? (
      <div
        ref={dropdownRef}
        style={{
          position: "fixed",
          top:
            dropdownPosition === "bottom" && buttonRef.current
              ? buttonRef.current.getBoundingClientRect().bottom + 4
              : undefined,
          bottom:
            dropdownPosition === "top" && buttonRef.current
              ? window.innerHeight -
                buttonRef.current.getBoundingClientRect().top +
                4
              : undefined,
          left: buttonRef.current
            ? buttonRef.current.getBoundingClientRect().left
            : 0,
          width: buttonRef.current
            ? buttonRef.current.getBoundingClientRect().width
            : 300,
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
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              className="w-full bg-transparent pl-8 pr-8 py-1.5 text-sm rounded-sm outline-none placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Type to search..."
            />
            {loading && (
              <Loader2 className="absolute right-2.5 size-4 animate-spin opacity-50" />
            )}
          </div>
        </div>
        <div className="max-h-60 overflow-y-auto p-1" onScroll={handleScroll}>
          {loading && options.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Searching...
            </div>
          ) : options.length > 0 ? (
            options.map((opt, idx) => {
              const subtitles = getSubtitles(opt);
              return (
                <div
                  key={`${opt.value}-${idx}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleSelect(opt);
                  }}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  className={cn(
                    "relative flex w-full cursor-default items-center rounded-sm px-2 py-1.5 text-sm outline-none select-none transition-colors justify-between",
                    highlightedIndex === idx
                      ? "bg-accent text-accent-foreground"
                      : "",
                    opt.value === value ? "bg-accent/50" : "",
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
                  {opt.value === value && (
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
      </div>
    ) : null;

  return (
    <div
      ref={containerRef}
      onBlur={(e) => {
        if (
          !containerRef.current?.contains(e.relatedTarget as Node) &&
          !isSelectingRef.current
        ) {
          onBlur?.();
        }
      }}
      className={cn("relative w-full flex flex-col gap-1.5", className)}
    >
      {displayLabel && (
        <label className="text-sm font-medium text-foreground flex items-center gap-0.5 select-none">
          {displayLabel}
          {required && (
            <span className="text-destructive font-bold text-red-500 ml-0.5">
              *
            </span>
          )}
        </label>
      )}
      <div
        ref={buttonRef}
        onClick={handleOpen}
        className={cn(
          "border-input data-[placeholder]:text-muted-foreground [&_svg:not([class*='text-'])]:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 dark:bg-input/30 flex h-9 w-full items-center justify-between gap-2 rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs transition-[color,box-shadow] outline-none cursor-pointer",
          disabled && "opacity-50 cursor-not-allowed",
          isOpen && "ring-[3px] ring-ring/50 border-ring",
        )}
      >
        <span
          className={cn("truncate", !selectedOption && "text-muted-foreground")}
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          {clearable && selectedOption && value && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleClear();
              }}
              className="p-0.5 hover:bg-accent rounded text-muted-foreground hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          )}
          <ChevronDown
            className={cn(
              "size-4 opacity-50 transition-transform duration-200",
              isOpen && "rotate-180",
            )}
          />
        </div>
      </div>
      {typeof window !== "undefined" && createPortal(dropdown, document.body)}
    </div>
  );
};
