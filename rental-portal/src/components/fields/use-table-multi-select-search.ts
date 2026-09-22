/**
 * useTableMultiSelectSearch – handles searching, infinite scroll, and keyboard navigation for TableMultiSelect.
 *
 * Key dependencies: uses frappe-service search_link API call, manages request cancellation via ref counters.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { useCallPost } from "@/lib/frappe-service";
import type { DropdownOption } from "./table-multi-select-types";

interface UseTableMultiSelectSearchResult {
  options: DropdownOption[];
  loading: boolean;
  highlightedIndex: number;
  search: string;
  isSelectingRef: React.MutableRefObject<boolean>;
  hasFetchedOnceRef: React.MutableRefObject<boolean>;
  performSearch: (searchTerm: string, limit: number, append?: boolean) => Promise<void>;
  setOptions: React.Dispatch<React.SetStateAction<DropdownOption[]>>;
  setSearch: React.Dispatch<React.SetStateAction<string>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setHighlightedIndex: React.Dispatch<React.SetStateAction<number>>;
  lastSearchedTxtRef: React.MutableRefObject<string | null>;
  inputRef: React.RefObject<HTMLInputElement | null>;
}

/**
 * Hook managing search state, API calls, and request deduplication.
 *
 * Args:
 *   linkDoctype: The target doctype to search in.
 *   referenceDoctype: The source doctype (for context).
 *   query: Optional custom query method name.
 *   filters: Optional filters to apply.
 *   debounceDelay: Debounce delay in ms.
 *   pageLength: Number of results per page.
 *
 * Returns:
 *   Search state and handlers.
 */
export function useTableMultiSelectSearch(
  linkDoctype: string,
  referenceDoctype: string,
  query?: string,
  filters: Record<string, any> = {},
  debounceDelay: number = 300,
  _pageLength: number = 20,
): UseTableMultiSelectSearchResult {
  const [options, setOptions] = useState<DropdownOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const searchTimeoutRef = useRef<any>(null);
  const isSelectingRef = useRef(false);
  const hasFetchedOnceRef = useRef(false);
  const lastSearchedTxtRef = useRef<string | null>(null);
  const activeRequestIdRef = useRef<number>(0);
  const hasMoreRef = useRef<boolean>(true);
  const isFetchingMoreRef = useRef<boolean>(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { post: searchLink } = useCallPost("frappe.desk.search.search_link");

  const performSearch = useCallback(
    async (searchTerm: string, limit: number, append = false) => {
      if (!linkDoctype) return;
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
            doctype: linkDoctype,
            reference_doctype: referenceDoctype,
            page_length: limit,
            query: query || undefined,
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

          hasMoreRef.current = results.length >= limit;

          if (!isSelectingRef.current) {
            if (append) {
              setOptions((prev) => {
                const existingValues = new Set(prev.map((o) => o.value));
                const filteredNew = results.filter((o: any) => !existingValues.has(o.value));
                return [...prev, ...filteredNew];
              });
            } else {
              setOptions(results);
              lastSearchedTxtRef.current = searchTerm;
            }
          }
        } catch {
          // Request failed silently; stale responses are discarded via requestId
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
    [linkDoctype, referenceDoctype, query, filters, debounceDelay, searchLink],
  );

  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  return {
    options,
    loading,
    highlightedIndex,
    search,
    isSelectingRef,
    hasFetchedOnceRef,
    performSearch,
    setOptions,
    setSearch,
    setLoading,
    setHighlightedIndex,
    lastSearchedTxtRef,
    inputRef,
  };
}