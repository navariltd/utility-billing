/** Renders a single field with label, required marker, readonly/hidden handling. */

import { cn } from "@/lib/utils";
import { FrappeField } from "@/components/fields/FrappeField";
import type { FrappeFieldMeta } from "../types";

interface FieldItemProps {
  field: FrappeFieldMeta;
  value: any;
  doctype: string;
  disabled: boolean;
  isNew: boolean;
  onChange: (value: any, fieldname?: string) => void;
  fullWidth?: boolean;
}

export function FieldItem({ field, value, doctype, disabled, isNew: _isNew, onChange, fullWidth }: FieldItemProps) {
  const isHidden = field.hidden || (field.read_only && !value && value !== 0 && value !== false);
  if (isHidden) return null;

  // When disabled (read-only) and field has no meaningful value, hide it
  const hasValue = value !== undefined && value !== null && value !== "" && value !== 0 && value !== false;
  if (disabled && !hasValue) {
    return null;
  }

  // Table fieldtypes should always span full width regardless of column count
  const isTable = field.fieldtype === "Table";
  const shouldUseFullWidth = fullWidth || isTable;

  const defaultValue = field.default !== undefined && field.default !== null && (value === undefined || value === null)
    ? field.default
    : value;

  return (
    <div className={cn("flex flex-col", shouldUseFullWidth ? "col-span-full w-full" : "w-full")}>
      <FrappeField
        field={field}
        value={defaultValue}
        onChange={onChange}
        doctype={doctype}
        disabled={disabled || field.read_only}
        showLabel={true}
      />
    </div>
  );
}
