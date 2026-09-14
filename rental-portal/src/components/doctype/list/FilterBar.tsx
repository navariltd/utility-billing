/** Inline filter bar with standard filters on left, Add Filter on far right, always-show Clear. */

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { FrappeField } from "@/components/fields/FrappeField";
import { FilterDropdown } from "../FilterDropdown";
import { DOCSTATUS_MAP, type ActiveFilter, type FilterItem } from "../types";
import { getOperatorsForFieldtype } from "../utils";

interface FilterBarProps {
  standardFilterFields: any[];
  activeFilters: Record<string, ActiveFilter>;
  onFilterChange: (fieldname: string, operator: string, value: string) => void;
  onRemoveFilter: (fieldname: string) => void;
  onClearFilters: () => void;
  filterDropdownOpen: boolean;
  onFilterDropdownOpenChange: (open: boolean) => void;
  filterRows: FilterItem[];
  onSetFilterRows: (rows: FilterItem[]) => void;
  filterableFields: any[];
  onApplyFilters: () => void;
  schemaFields: any[];
}

export function FilterBar({
  standardFilterFields, activeFilters, onFilterChange, onRemoveFilter, onClearFilters,
  filterDropdownOpen, onFilterDropdownOpenChange, filterRows, onSetFilterRows,
  filterableFields, onApplyFilters, schemaFields,
}: FilterBarProps) {
  const filterKeys = Object.keys(activeFilters);
  const hasActiveFilters = filterKeys.some((k) => k !== "name" && activeFilters[k].value !== "");
  const appliedFilterCount = filterKeys.filter((k) => k !== "name" && activeFilters[k].value !== "").length;

  return (
    <div className="bg-muted/30 border rounded-lg p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {/* Left side: standard filters */}
        <div className="flex-1 min-w-[150px] max-w-[220px]">
          <Input placeholder="ID" value={activeFilters["name"]?.value || ""}
            onChange={(e) => onFilterChange("name", "like", e.target.value)} className="h-9 text-sm bg-background" />
        </div>
        {standardFilterFields.map((f: any) => {
          const filter = activeFilters[f.fieldname] || { value: "", operator: "like", fieldtype: f.fieldtype };
          return (
            <div key={f.fieldname} className="flex-1 min-w-[150px] max-w-[220px]">
              {f.fieldtype === "Select" ? (
                <Select value={filter.value} onValueChange={(v) => onFilterChange(f.fieldname, "=", v === "__all" ? "" : v)}>
                  <SelectTrigger className="h-9 text-sm bg-background"><SelectValue placeholder={f.label || f.fieldname} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all">All {f.label || f.fieldname}</SelectItem>
                    {(typeof f.options === "string" ? f.options.split("\n").filter(Boolean) : Array.isArray(f.options) ? f.options : []).map((opt: any) => {
                      const val = typeof opt === "string" ? opt : opt.value;
                      return <SelectItem key={val} value={val}>{typeof opt === "string" ? opt.replace(/_/g, " ") : opt.label || opt.value}</SelectItem>;
                    })}
                  </SelectContent>
                </Select>
              ) : f.fieldtype === "Link" ? (
                <div className="bg-background rounded-md">
                  <FrappeField field={{ ...f, fieldname: f.fieldname, placeholder: f.label || f.fieldname } as any}
                    value={filter.value} onChange={(val: any) => onFilterChange(f.fieldname, "=", val || "")} doctype={f.options} showLabel={false} />
                </div>
              ) : (
                <Input placeholder={f.label || f.fieldname} value={filter.value}
                  onChange={(e) => onFilterChange(f.fieldname, "like", e.target.value)} className="h-9 text-sm bg-background" />
              )}
            </div>
          );
        })}

        {/* Spacer pushes Add Filter + Clear to far right */}
        <div className="flex-1" />

        {/* Far right: Add Filter dropdown + Clear button */}
        <div className="flex items-center gap-2 shrink-0">
          <FilterDropdown
            open={filterDropdownOpen}
            onOpenChange={onFilterDropdownOpenChange}
            filterRows={filterRows}
            onSetFilterRows={onSetFilterRows}
            filterableFields={filterableFields}
            onApplyFilters={onApplyFilters}
            appliedFilterKeys={filterKeys.filter((k) => k !== "name" && activeFilters[k].value !== "")}
          />
          <Button variant="ghost" size="sm" onClick={onClearFilters} className="h-9 text-xs text-muted-foreground shrink-0">
            Clear {appliedFilterCount > 0 ? `(${appliedFilterCount})` : ""}
          </Button>
        </div>
      </div>

      {/* Active filter badges (non-standard, non-name) */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {filterKeys.filter((k) => k !== "name" && activeFilters[k].value !== "").map((key) => {
            const f = activeFilters[key];
            const label = key === "docstatus" ? "Status" : schemaFields.find((sf: any) => sf.fieldname === key)?.label || key;
            const displayVal = key === "docstatus" ? DOCSTATUS_MAP[Number(f.value)]?.label || f.value : f.value;
            const opLabel = getOperatorsForFieldtype(f.fieldtype).find((o) => o.value === f.operator)?.label || f.operator;
            return (
              <Badge key={key} variant="secondary" className="text-xs gap-1 pl-2 pr-1 py-0.5 font-normal">
                <span className="font-medium">{label}</span><span className="text-muted-foreground">{opLabel}</span><span>{displayVal}</span>
                <button onClick={() => onRemoveFilter(key)} className="ml-0.5 hover:text-destructive"><X className="h-3 w-3" /></button>
              </Badge>
            );
          })}
        </div>
      )}
    </div>
  );
}