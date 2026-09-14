"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChevronDown, ChevronRight, Eye, Pencil } from "lucide-react";
import { FrappeField, type FrappeFieldMeta } from "../FrappeField";
import { buildFormLayout } from "./formLayout";
import type { DoctypeField, FormSection } from "./types";

interface RowEditModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rowData: Record<string, any>;
  allFields: DoctypeField[];
  onSave: (data: Record<string, any>) => void;
  /** If true, renders in read-only view mode (no edit/save, just display). Defaults to false. */
  readOnly?: boolean;
}

/**
 * Normalize a Frappe DocField (with 0/1 booleans) into FrappeFieldMeta (with proper booleans).
 */
function toFrappeFieldMeta(field: DoctypeField): FrappeFieldMeta {
  const meta: FrappeFieldMeta = {
    fieldname: field.fieldname,
    label: field.label,
    fieldtype: field.fieldtype,
    options: field.options,
    default: field.default,
    placeholder: field.placeholder,
    reqd: field.reqd === 1,
    read_only: field.read_only === 1,
    hidden: field.hidden === 1,
    in_list_view: field.in_list_view === 1,
    collapsible: field.collapsible === 1,
    collapsed: field.collapsed === 1,
    depends_on: field.depends_on,
    description: field.description,
    bold: field.bold === 1,
    allow_on_submit: field.allow_on_submit === 1,
    unique: field.unique === 1,
    no_copy: field.no_copy === 1,
    permlevel: field.permlevel,
    translatable: field.translatable === 1,
    hide_days: field.hide_days === 1,
    hide_seconds: field.hide_seconds === 1,
    non_negative: field.non_negative === 1,
    allow_in_quick_entry: field.allow_in_quick_entry === 1,
    search_index: field.search_index === 1,
    in_global_search: field.in_global_search === 1,
    in_filter: field.in_filter === 1,
    in_preview: field.in_preview === 1,
    in_standard_filter: field.in_standard_filter === 1,
    allow_bulk_edit: field.allow_bulk_edit === 1,
    print_hide: field.print_hide === 1,
    print_hide_if_no_value: field.print_hide_if_no_value === 1,
    max_height: field.max_height,
    precision: field.precision,
    length: field.length,
    regex: field.regex,
    max_value: field.max_value,
    min_value: field.min_value,
    max_length: field.max_length,
    min_length: field.min_length,
    fetch_from: field.fetch_from,
    remember_last_used_value: field.remember_last_selected_value === 1,
    sortable: field.sortable === 1,
  };
  // Copy over numeric 'columns' as number only if defined
  if (field.columns !== undefined) {
    meta.columns = field.columns;
  }
  return meta;
}

export const RowEditModal = ({
  open,
  onOpenChange,
  rowData,
  allFields,
  onSave,
  readOnly = false,
}: RowEditModalProps) => {
  const [editData, setEditData] = React.useState<Record<string, any>>({});

  React.useEffect(() => {
    if (open) {
      setEditData({ ...rowData });
    }
  }, [open, rowData]);

  const handleFieldChange = (fieldname: string, val: any) => {
    if (readOnly) return;
    setEditData((prev) => ({ ...prev, [fieldname]: val }));
  };

  const handleSave = () => {
    onSave(editData);
    onOpenChange(false);
  };

  const tabs = React.useMemo(() => buildFormLayout(allFields), [allFields]);

  // Track collapsed state for collapsible sections
  const [collapsedSections, setCollapsedSections] = React.useState<
    Record<string, boolean>
  >({});

  React.useEffect(() => {
    if (open) {
      const initial: Record<string, boolean> = {};
      allFields.forEach((f) => {
        if (f.fieldtype === "Section Break" && f.collapsible === 1) {
          // If collapsible, default to collapsed (true) unless explicitly set to 0
          initial[f.label || f.fieldname || `section_${f.idx}`] =
            f.collapsed !== 0;
        }
      });
      setCollapsedSections(initial);
    }
  }, [open, allFields]);

  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // In read-only mode, filter out fields with no value
  const hasVisibleContent = React.useCallback(
    (fields: DoctypeField[]) => {
      return fields.some((field) => {
        if (["Tab Break", "Section Break", "Column Break", "Heading", "Fold"].includes(field.fieldtype)) return false;
        if (field.hidden === 1) return false;
        if (readOnly) {
          const val = editData[field.fieldname];
          const hasValue = val !== undefined && val !== null && val !== "" && val !== 0;
          return hasValue;
        }
        return true;
      });
    },
    [readOnly, editData]
  );

  const renderFormFields = (fields: DoctypeField[]) => {
    return fields
      .map((field) => {
        const ft = field.fieldtype;
        if (["Tab Break", "Section Break", "Column Break", "Heading", "Fold"].includes(ft)) return null;
        if (field.hidden === 1) return null;

        const val = editData[field.fieldname];
        // In read-only mode, skip fields with no value
        if (readOnly) {
          const hasValue = val !== undefined && val !== null && val !== "" && val !== 0;
          if (!hasValue) return null;
        }

        const meta = toFrappeFieldMeta(field);
        return (
          <FrappeField
            key={field.fieldname}
            field={meta}
            value={val}
            onChange={(v: any) => handleFieldChange(field.fieldname, v)}
            showLabel
            disabled={readOnly}
          />
        );
      })
      .filter(Boolean);
  };

  const renderSections = (sections: FormSection[]) => {
    return sections
      .map((section, si) => {
        // In read-only mode, skip sections with no visible content
        if (readOnly) {
          const hasVisible = section.columns.some((col) =>
            col.fields.some((f) => hasVisibleContent([f]))
          );
          if (!hasVisible) return null;
        }

        const sectionKey = section.label || `section_${si}`;
        const isCollapsed = collapsedSections[sectionKey] ?? false;

        const renderedColumns = section.columns.map((col, ci) => {
          const renderedFields = renderFormFields(col.fields);
          if (readOnly && renderedFields.length === 0) return null;
          return (
            <div key={ci} className="flex flex-col gap-3">
              {renderedFields}
            </div>
          );
        }).filter(Boolean);

        if (readOnly && renderedColumns.length === 0) return null;

        return (
          <div key={si} className="mb-6 last:mb-0">
            {section.label && (
              <div className="flex items-center gap-2 mb-3 pb-1 border-b border-border">
                {section.collapsible ? (
                  <button
                    type="button"
                    onClick={() => toggleSection(sectionKey)}
                    className="flex items-center gap-1.5 text-sm font-semibold text-foreground hover:text-primary transition-colors"
                  >
                    {isCollapsed ? (
                      <ChevronRight className="size-4" />
                    ) : (
                      <ChevronDown className="size-4" />
                    )}
                    {section.label}
                  </button>
                ) : (
                  <h4 className="text-sm font-semibold text-foreground">
                    {section.label}
                  </h4>
                )}
              </div>
            )}
            {(!section.collapsible || !isCollapsed) && (
              <div
                className={cn("grid gap-4", "grid-cols-1")}
                style={
                  section.columns.length > 1
                    ? ({
                        gridTemplateColumns: `repeat(${Math.min(
                          section.columns.length,
                          3,
                        )}, 1fr)`,
                      } as React.CSSProperties)
                    : undefined
                }
              >
                {renderedColumns}
              </div>
            )}
          </div>
        );
      })
      .filter(Boolean);
  };

  const title = readOnly ? "View Row" : "Edit Row";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <style>{`
        [data-slot="dialog-overlay"] {
          backdrop-filter: blur(4px);
          -webkit-backdrop-filter: blur(4px);
        }
      `}</style>
      <DialogContent className="sm:max-w-3xl lg:max-w-4xl max-h-[90vh] overflow-y-auto border-primary/20 shadow-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {readOnly ? <Eye className="size-4" /> : <Pencil className="size-4" />}
            {title}
          </DialogTitle>
        </DialogHeader>

        {tabs.length > 1 ? (
          <Tabs defaultValue={tabs[0]?.label || "Default"} className="w-full">
            <TabsList className="mb-4 flex-wrap">
              {tabs.map((tab) => (
                <TabsTrigger key={tab.label} value={tab.label}>
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {tabs.map((tab) => (
              <TabsContent key={tab.label} value={tab.label}>
                {renderSections(tab.sections)}
              </TabsContent>
            ))}
          </Tabs>
        ) : (
          <div className="space-y-6">
            {tabs[0] && renderSections(tabs[0].sections)}
            {readOnly && renderSections(tabs[0]?.sections || []).length === 0 && (
              <div className="text-center py-8 text-muted-foreground text-sm">
                No data to display.
              </div>
            )}
          </div>
        )}

        {!readOnly && (
          <DialogFooter className="mt-6 pt-4 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="button" onClick={handleSave}>
              Save
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
};