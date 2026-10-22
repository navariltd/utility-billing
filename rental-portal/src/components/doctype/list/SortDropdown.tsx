/** Sort field/order popover. */

import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface SortDropdownProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fields: { value: string; label: string }[];
  sortField: string;
  sortOrder: "asc" | "desc";
  onSortFieldChange: (field: string) => void;
  onSortOrderChange: (order: "asc" | "desc") => void;
}

export function SortDropdown({ open, onOpenChange, fields, sortField, sortOrder, onSortFieldChange, onSortOrderChange }: SortDropdownProps) {
  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1 text-xs h-8">
          <ArrowUpDown className="h-3.5 w-3.5" />
          {fields.find((f) => f.value === sortField)?.label || sortField}
          <span className="text-muted-foreground">{sortOrder === "desc" ? "↓" : "↑"}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-2" align="end">
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Sort by</p>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {fields.map((f) => (
              <button key={f.value} onClick={() => { onSortFieldChange(f.value); onOpenChange(false); }}
                className={cn("w-full text-left px-2 py-1.5 text-sm rounded-md hover:bg-muted", sortField === f.value && "bg-muted font-medium")}>
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between pt-2 border-t">
            <span className="text-xs text-muted-foreground">Order</span>
            <div className="flex gap-1">
              <Button variant={sortOrder === "asc" ? "default" : "outline"} size="sm" className="h-7 text-xs px-2" onClick={() => onSortOrderChange("asc")}>Asc</Button>
              <Button variant={sortOrder === "desc" ? "default" : "outline"} size="sm" className="h-7 text-xs px-2" onClick={() => onSortOrderChange("desc")}>Desc</Button>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}