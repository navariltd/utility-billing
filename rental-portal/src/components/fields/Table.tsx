"use client";

import { useCallPost } from "@/lib/frappe-service";
import { cn } from "@/lib/utils";
import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import * as React from "react";

import { renderCellField } from "./table/CellRenderer";
import { RowEditModal } from "./table/RowEditModal";
import {
  STICKY_CELL_CLASS,
  STICKY_RIGHT_CLASS,
  STICKY_RIGHT_HEADER_CLASS,
  getStickyStyle,
} from "./table/stickyHelpers";
import type { DoctypeField, TableProps } from "./table/types";

export const Table = ({
  doctype,
  value = [],
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  stickyColumns = 1,
}: TableProps) => {
  const [fields, setFields] = React.useState<DoctypeField[]>([]);
  const [allFields, setAllFields] = React.useState<DoctypeField[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [editIndex, setEditIndex] = React.useState<number | null>(null);

  const { post: fetchDocType } = useCallPost("frappe.desk.form.load.getdoctype");

  React.useEffect(() => {
    const loadMeta = async () => {
      if (!doctype) return;
      try {
        setLoading(true);
        const response = await fetchDocType({
          doctype: doctype,
          with_parent: 0,
        });
        if (response && (response as any).docs && (response as any).docs[0]) {
          const docMeta = (response as any).docs[0];
          const listFields = (docMeta.fields || []).filter(
            (f: any) => f.in_list_view === 1,
          );
          setFields(listFields);
          setAllFields(docMeta.fields || []);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadMeta();
  }, [doctype]);

  const handleAddField = () => {
    const newRow = fields.reduce(
      (acc, field) => {
        let defaultValue: any = "";
        switch (field.fieldtype) {
          case "Check":
            defaultValue = 0;
            break;
          case "Int":
          case "Float":
          case "Currency":
          case "Percent":
            defaultValue = 0;
            break;
          case "Select":
            defaultValue = field.options?.split("\n")[0] || "";
            break;
          case "Table MultiSelect":
            defaultValue = [];
            break;
          default:
            defaultValue = field.default ?? "";
        }
        acc[field.fieldname] = defaultValue;
        return acc;
      },
      {} as Record<string, any>,
    );

    onChange([...value, newRow]);
  };

  const handleRemoveField = (index: number) => {
    const updated = value.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleCellChange = (index: number, fieldname: string, val: any) => {
    const updated = value.map((row, i) => {
      if (i === index) {
        return { ...row, [fieldname]: val };
      }
      return row;
    });
    onChange(updated);
  };

  const handleEditSave = (data: Record<string, any>) => {
    if (editIndex === null) return;
    const updated = value.map((row, i) => {
      if (i === editIndex) {
        return { ...data };
      }
      return row;
    });
    onChange(updated);
    setEditIndex(null);
  };

  // When disabled (read-only) and no data: hide the entire table
  const isEmpty = !Array.isArray(value) || value.length === 0;
  if (disabled && isEmpty) {
    return null;
  }

  // Disabled mode: hide action buttons except view (pencil)
  const showActions = !disabled;

  const displayLabel = label || doctype;
  const stickyLeftCount = Math.min(stickyColumns, fields.length);

  return (
    <div
      onBlur={onBlur}
      className={cn("w-full flex flex-col gap-1.5", className)}
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

      {loading ? (
        <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground justify-center border rounded-md border-dashed">
          <Loader2 className="size-4 animate-spin" />
          Loading table fields...
        </div>
      ) : (
        <div className="border rounded-md overflow-hidden bg-background">
          <div className="overflow-x-auto w-full">
            <table className="w-full text-sm border-collapse text-left">
              <thead>
                <tr className="border-b bg-background transition-colors">
                  {fields.map((field, fi) => (
                    <th
                      key={field.fieldname}
                      className={cn(
                        "h-10 px-3 text-left align-middle font-medium text-muted-foreground border-r last:border-r-0 min-w-[120px]",
                        fi < stickyLeftCount && STICKY_CELL_CLASS,
                      )}
                      style={
                        fi < stickyLeftCount
                          ? getStickyStyle(fi, stickyLeftCount)
                          : undefined
                      }
                    >
                      {field.label}
                      {field.reqd === 1 && (
                        <span className="text-destructive font-bold text-red-500 ml-0.5">
                          *
                        </span>
                      )}
                    </th>
                  ))}
                  {showActions && (
                    <th
                      className={cn(
                        "h-10 w-[88px] px-3 text-center align-middle font-medium text-muted-foreground",
                        STICKY_RIGHT_HEADER_CLASS,
                      )}
                    >
                      Actions
                    </th>
                  )}
                  {/* Always show a narrow column for the view button even in readonly */}
                  {!showActions && (
                    <th
                      className={cn(
                        "h-10 w-[44px] px-1 text-center align-middle font-medium text-muted-foreground",
                        STICKY_RIGHT_HEADER_CLASS,
                      )}
                    >
                      <span className="sr-only">View</span>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {!Array.isArray(value) || value.length === 0 ? (
                  <tr>
                    <td
                      colSpan={fields.length + 1}
                      className="p-4 text-center text-muted-foreground text-xs"
                    >
                      No rows added yet.
                    </td>
                  </tr>
                ) : (
                  value.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className="border-b last:border-b-0 hover:bg-muted/20 transition-colors"
                    >
                      {fields.map((field, fi) => (
                        <td
                          key={field.fieldname}
                          className={cn(
                            "p-1 border-r last:border-r-0 align-middle",
                            fi < stickyLeftCount && STICKY_CELL_CLASS,
                          )}
                          style={
                            fi < stickyLeftCount
                              ? getStickyStyle(fi, stickyLeftCount)
                              : undefined
                          }
                        >
                          {renderCellField(
                            field,
                            row,
                            rowIndex,
                            disabled,
                            handleCellChange,
                          )}
                        </td>
                      ))}
                      <td
                        className={cn(
                          "p-1 text-center align-middle",
                          STICKY_RIGHT_CLASS,
                        )}
                      >
                        <div className="flex items-center justify-center gap-0.5">
                          <button
                            type="button"
                            onClick={() => setEditIndex(rowIndex)}
                            className="p-1.5 hover:bg-primary/10 text-muted-foreground hover:text-primary rounded-md transition-colors"
                            title={disabled ? "View row" : "Edit row"}
                          >
                            <Pencil className="size-3.5" />
                          </button>
                          {showActions && (
                            <button
                              type="button"
                              onClick={() => handleRemoveField(rowIndex)}
                              className="p-1.5 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-md transition-colors"
                              title="Delete row"
                            >
                              <Trash2 className="size-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {showActions && (
            <div className="p-2 border-t bg-muted/20 flex justify-start">
              <button
                type="button"
                disabled={disabled || fields.length === 0}
                onClick={handleAddField}
                className="flex items-center gap-1.5 text-xs font-medium border px-2.5 py-1.5 rounded-md bg-background shadow-xs hover:bg-muted transition-colors disabled:opacity-50"
              >
                <Plus className="size-3.5" />
                Add Row
              </button>
            </div>
          )}
        </div>
      )}

      {/* Row Edit Modal - opens in read-only mode when disabled */}
      {editIndex !== null && value[editIndex] && (
        <RowEditModal
          open={editIndex !== null}
          onOpenChange={(open) => {
            if (!open) setEditIndex(null);
          }}
          rowData={value[editIndex]}
          allFields={allFields}
          onSave={handleEditSave}
          readOnly={disabled}
        />
      )}
    </div>
  );
};

export default Table;
