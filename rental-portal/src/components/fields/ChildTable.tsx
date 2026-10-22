"use client";

import { useCallPost } from "@/lib/frappe-service";
import { cn } from "@/lib/utils";
import { Loader2, Plus, Trash2 } from "lucide-react";
import * as React from "react";

interface ChildTableProps {
  doctype: string;
  value: any[];
  onChange: (val: any[]) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
}

interface DoctypeField {
  fieldname: string;
  label: string;
  fieldtype: string;
  in_list_view?: number;
}

export const ChildTable = ({
  doctype,
  value = [],
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
}: ChildTableProps) => {
  const [fields, setFields] = React.useState<DoctypeField[]>([]);
  const [loading, setLoading] = React.useState(false);

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
        acc[field.fieldname] = "";
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

  const handleCellChange = (index: number, fieldname: string, val: string) => {
    const updated = value.map((row, i) => {
      if (i === index) {
        return { ...row, [fieldname]: val };
      }
      return row;
    });
    onChange(updated);
  };

  const displayLabel = label || doctype;

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
                <tr className="border-b bg-muted/40 transition-colors">
                  {fields.map((field) => (
                    <th
                      key={field.fieldname}
                      className="h-10 px-3 text-left align-middle font-medium text-muted-foreground border-r last:border-r-0"
                    >
                      {field.label}
                    </th>
                  ))}
                  <th className="h-10 w-12 px-3 text-center align-middle font-medium text-muted-foreground"></th>
                </tr>
              </thead>
              <tbody>
                {value.length === 0 ? (
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
                      {fields.map((field) => (
                        <td
                          key={field.fieldname}
                          className="p-1 border-r last:border-r-0 align-middle"
                        >
                          <input
                            type="text"
                            disabled={disabled}
                            value={row[field.fieldname] || ""}
                            onChange={(e) =>
                              handleCellChange(
                                rowIndex,
                                field.fieldname,
                                e.target.value,
                              )
                            }
                            className="w-full bg-transparent px-2 py-1 text-sm rounded-xs outline-none focus-visible:bg-muted/50 transition-colors"
                            placeholder={`Enter ${field.label}...`}
                          />
                        </td>
                      ))}
                      <td className="p-1 text-center align-middle">
                        <button
                          type="button"
                          disabled={disabled}
                          onClick={() => handleRemoveField(rowIndex)}
                          className="p-1.5 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-md transition-colors disabled:opacity-50"
                        >
                          <Trash2 className="size-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="p-2 border-t bg-muted/20 flex justify-end">
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
        </div>
      )}
    </div>
  );
};
