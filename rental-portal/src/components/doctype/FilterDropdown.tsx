/** Frappe-style multi-row filter builder. Shows ALL filters as editable rows. */

"use client";

import { X, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { FrappeField } from "@/components/fields/FrappeField";
import { type FilterItem, type FrappeFieldMeta } from "./types";
import { getOperatorsForFieldtype, getInputTypeForFieldtype } from "./utils";

interface FilterDropdownProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** All rows: currently set filters + new pending rows. Merged view. */
  filterRows: FilterItem[];
  onSetFilterRows: (rows: FilterItem[]) => void;
  filterableFields: FrappeFieldMeta[];
  onApplyFilters: () => void;
  /** Keys of rows that are currently applied (for visual indicator) */
  appliedFilterKeys: string[];
}

export function FilterDropdown({
  open,
  onOpenChange,
  filterRows,
  onSetFilterRows,
  filterableFields,
  onApplyFilters,
  appliedFilterKeys,
}: FilterDropdownProps) {
  const updateRow = (index: number, patch: Partial<FilterItem>) => {
    onSetFilterRows(
      filterRows.map((f, i) => (i === index ? { ...f, ...patch } : f)),
    );
  };

  const removeRow = (index: number) => {
    onSetFilterRows(filterRows.filter((_, i) => i !== index));
  };

  const addRow = () => {
    onSetFilterRows([
      ...filterRows,
      { fieldname: "", operator: "like", value: "", fieldtype: "Data" },
    ]);
  };

  const handleFieldChange = (index: number, v: string) => {
    const fc = filterableFields.find((f: any) => f.fieldname === v);
    updateRow(index, {
      fieldname: v,
      operator:
        fc?.fieldtype === "Select" || fc?.fieldtype === "Link" ? "=" : "like",
      value: "",
      fieldtype: fc?.fieldtype || "Data",
    });
  };

  const getFieldConfig = (fieldname: string) =>
    fieldname ? filterableFields.find((f) => f.fieldname === fieldname) : null;

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <Button variant="secondary" size="sm" className="h-9 gap-2 px-3 shrink-0">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          <span>Add Filter</span>
          {appliedFilterKeys.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold bg-primary text-primary-foreground rounded-full">
              {appliedFilterKeys.length}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[700px] max-w-[90vw] p-0" align="start" sideOffset={4}>
        <div className="p-4 pb-0">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold">Filters</p>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => onOpenChange(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* All filter rows (active + pending) */}
          <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
            {filterRows.map((pf, index) => {
              const fc = getFieldConfig(pf.fieldname);
              const isApplied = appliedFilterKeys.includes(pf.fieldname);
              return (
                <div
                  key={index}
                  className={`flex items-start gap-2 p-2 border rounded-md bg-background ${
                    isApplied ? "border-primary/30 ring-1 ring-primary/10" : ""
                  }`}
                >
                  <div className="flex-1 min-w-0 space-y-0.5">
                    <label className="text-[9px] uppercase text-muted-foreground font-semibold tracking-wider">Field</label>
                    <Select value={pf.fieldname} onValueChange={(v) => handleFieldChange(index, v)}>
                      <SelectTrigger className="h-8 text-xs w-full">
                        <SelectValue placeholder="Select field" />
                      </SelectTrigger>
                      <SelectContent>
                        {filterableFields.map((f: any) => (
                          <SelectItem key={f.fieldname} value={f.fieldname}>
                            {f.label || f.fieldname}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {pf.fieldname && (
                    <>
                      <div className="flex-1 min-w-0 space-y-0.5">
                        <label className="text-[9px] uppercase text-muted-foreground font-semibold tracking-wider">Condition</label>
                        <Select value={pf.operator} onValueChange={(v) => updateRow(index, { operator: v })}>
                          <SelectTrigger className="h-8 text-xs w-full">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {getOperatorsForFieldtype(pf.fieldtype).map((op) => (
                              <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex-1 min-w-0 space-y-0.5">
                        <label className="text-[9px] uppercase text-muted-foreground font-semibold tracking-wider">Value</label>
                        {pf.fieldtype === "Select" && fc ? (
                          <Select value={pf.value} onValueChange={(v) => updateRow(index, { value: v })}>
                            <SelectTrigger className="h-8 text-xs w-full">
                              <SelectValue placeholder="Select" />
                            </SelectTrigger>
                            <SelectContent>
                              {(typeof fc.options === "string"
                                ? fc.options.split("\n").filter(Boolean)
                                : Array.isArray(fc.options) ? fc.options : []
                              ).map((opt: any) => {
                                const val = typeof opt === "string" ? opt : opt.value;
                                return <SelectItem key={val} value={val}>{typeof opt === "string" ? opt.replace(/_/g, " ") : opt.label || opt.value}</SelectItem>;
                              })}
                            </SelectContent>
                          </Select>
                        ) : pf.fieldtype === "Link" ? (
                          <div className="bg-background rounded-md">
                            <FrappeField
                              field={{ fieldname: pf.fieldname, fieldtype: "Link", options: fc?.options } as any}
                              value={pf.value}
                              onChange={(val: any) => updateRow(index, { value: val || "" })}
                              doctype={typeof fc?.options === "string" ? fc.options : ""}
                              showLabel={false}
                            />
                          </div>
                        ) : (
                          <Input
                            type={getInputTypeForFieldtype(pf.fieldtype)}
                            value={pf.value}
                            onChange={(e) => updateRow(index, { value: e.target.value })}
                            placeholder="Value..."
                            className="h-8 text-xs w-full"
                          />
                        )}
                      </div>
                    </>
                  )}
                  <button
                    onClick={() => removeRow(index)}
                    className="mt-5 p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive shrink-0"
                    title="Remove filter"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>

          {/* Add row button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={addRow}
            className="mt-2 h-8 text-xs gap-1 w-full justify-start text-muted-foreground hover:text-foreground"
          >
            <Plus className="h-3.5 w-3.5" />
            Add another filter
          </Button>
        </div>

        {/* Footer with Apply */}
        <div className="flex items-center justify-end gap-2 p-4 border-t bg-muted/20">
          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={() => {
              onApplyFilters();
              onOpenChange(false);
            }}
            disabled={filterRows.every((f) => !f.fieldname || !f.value)}
          >
            Apply Filters
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}