/** Pagination controls with page size, quick date ranges, and page navigation. */

import { ChevronLeft, ChevronRight, Clock, ChevronDown } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { QUICK_DATE_RANGES } from "../utils";

const PAGE_SIZES = [25, 50, 100, 200, 500, 1000, 0];

interface PaginationBarProps {
  pageSize: number;
  onPageSizeChange: (size: number) => void;
  currentPage: number;
  totalPages: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onQuickDate: (range: (typeof QUICK_DATE_RANGES)[0]) => void;
  paginationPages: (number | "...")[];
}

export function PaginationBar({ pageSize, onPageSizeChange, currentPage, totalPages, totalCount, onPageChange, onQuickDate, paginationPages }: PaginationBarProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div className="flex items-center gap-3">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 text-xs gap-1 min-w-[90px] justify-between">
              {pageSize === 0 ? "All" : `${pageSize} / page`}
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[130px] p-1" align="start">
            {PAGE_SIZES.map((size) => (
              <button
                key={size}
                onClick={() => { onPageSizeChange(size); setOpen(false); }}
                className={cn(
                  "w-full text-left px-2.5 py-1.5 text-sm rounded-md hover:bg-muted transition-colors",
                  pageSize === size && "bg-muted font-medium",
                )}
              >
                {size === 0 ? "All" : `${size} / page`}
              </button>
            ))}
          </PopoverContent>
        </Popover>

        <div className="h-6 w-px bg-border" />
        <div className="flex items-center gap-0.5">
          <Clock className="h-3.5 w-3.5 text-muted-foreground mr-1" />
          {QUICK_DATE_RANGES.map((range) => (
            <Button key={range.value} variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
              onClick={() => onQuickDate(range)}>{range.label}</Button>
          ))}
        </div>
        <div className="h-6 w-px bg-border hidden sm:block" />
        {totalPages > 1 && <span className="text-xs text-muted-foreground whitespace-nowrap">Page {currentPage} of {totalPages} ({totalCount} entries)</span>}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon" className="h-8 w-8" disabled={currentPage <= 1} onClick={() => onPageChange(currentPage - 1)}><ChevronLeft className="h-4 w-4" /></Button>
          {paginationPages.map((page, idx) =>
            page === "..." ? <span key={`ellipsis-${idx}`} className="px-1 text-xs text-muted-foreground">···</span>
              : <Button key={page} variant={page === currentPage ? "default" : "outline"} size="icon" className="h-8 w-8 text-xs" onClick={() => onPageChange(page as number)}>{page}</Button>
          )}
          <Button variant="outline" size="icon" className="h-8 w-8" disabled={currentPage >= totalPages} onClick={() => onPageChange(currentPage + 1)}><ChevronRight className="h-4 w-4" /></Button>
        </div>
      )}
    </div>
  );
}