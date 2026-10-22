/** Section with collapsible support and column layout. Full-width fields when single column. */

import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { FieldItem } from "./FieldItem";
import type { SectionGroupV2 } from "../types";

interface FormSectionProps {
  section: SectionGroupV2;
  form: Record<string, any>;
  doctype: string;
  isReadOnly: boolean;
  isNew: boolean;
  onFieldChange: (value: any, fieldname?: string) => void;
  isCollapsed: boolean;
  onToggleSection: (fieldname: string) => void;
}

function hasVisibleFieldInSection(section: SectionGroupV2, form: Record<string, any>, isReadOnly: boolean): boolean {
  for (const col of section.columns) {
    for (const field of col.fields) {
      if (field.hidden) continue;
      if (!isReadOnly) return true;
      // In read-only mode, check if the field has a value
      const value = form[field.fieldname];
      if (value !== undefined && value !== null && value !== "" && value !== 0 && value !== false) {
        return true;
      }
    }
  }
  return false;
}

export function FormSection({ section, form, doctype, isReadOnly, isNew, onFieldChange, isCollapsed, onToggleSection }: FormSectionProps) {
  const colCount = section.columns?.length || 0;
  const isSingleColumn = colCount <= 1;

  // In read-only mode, skip section entirely if no fields have values
  if (isReadOnly && !hasVisibleFieldInSection(section, form, isReadOnly)) {
    return null;
  }

  return (
    <div className="border-b border-border/30">
      {section.label && (
        <div
          className={cn(
            "px-4 pt-3 pb-2 flex items-center gap-1 cursor-pointer select-none",
            section.collapsible && "hover:bg-muted/20 transition-colors",
          )}
          onClick={() => section.collapsible && onToggleSection(section.fieldname)}
        >
          <h3 className="text-sm font-semibold text-foreground/80">{section.label}</h3>
          {section.collapsible && (
            <button className="p-0.5 rounded hover:bg-muted text-muted-foreground shrink-0">
              {isCollapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
          )}
        </div>
      )}
      {!isCollapsed && (
        <div className={cn("px-4 py-3", !section.label && "pt-3")}>
          {isSingleColumn ? (
            // Single column: stack fields vertically, full width
            <div className="space-y-3">
              {section.columns[0]?.fields.map((field) => (
                <FieldItem
                  key={field.fieldname}
                  field={field}
                  value={form[field.fieldname]}
                  doctype={doctype}
                  disabled={isReadOnly}
                  isNew={isNew}
                  onChange={onFieldChange}
                />
              ))}
            </div>
          ) : (
            // Multi column: grid layout
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {section.columns.map((col) => {
                // If any field in this column is a Table, make the column span full width
                const hasTable = col.fields.some((f) => f.fieldtype === "Table");
                return (
                  <div key={col.fieldname} className={cn(hasTable && "col-span-full", "space-y-3")}>
                    {col.fields.map((field) => (
                      <FieldItem
                        key={field.fieldname}
                        field={field}
                        value={form[field.fieldname]}
                        doctype={doctype}
                        disabled={isReadOnly}
                        isNew={isNew}
                        onChange={onFieldChange}
                      />
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}