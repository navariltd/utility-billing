"use client";

import { cn } from "@/lib/utils";
import { Barcode } from "../Barcode";
import { ButtonField } from "../Button";
import { Check } from "../Check";
import { Code } from "../Code";
import { Color } from "../Color";
import { Currency } from "../Currency";
import { Data } from "../Data";
import { Date as DateField } from "../Date";
import { Datetime } from "../Datetime";
import { Duration } from "../Duration";
import { DynamicLink } from "../DynamicLink";
import { Float } from "../Float";
import { Geolocation } from "../Geolocation";
import { Heading } from "../Heading";
import { HTMLEditor } from "../HTMLEditor";
import { Icon } from "../Icon";
import { Image } from "../Image";
import { Int } from "../Int";
import { JSON as JSONField } from "../JSON";
import { LinkField } from "../LinkField";
import { LongText } from "../LongText";
import { MarkdownEditor } from "../MarkdownEditor";
import { Password } from "../Password";
import { Percent } from "../Percent";
import { Phone } from "../Phone";
import { Rating } from "../Rating";
import { Select } from "../Select";
import { Signature } from "../Signature";
import { SmallText } from "../SmallText";
import { TableMultiSelect } from "../TableMultiSelect";
import { Text } from "../Text";
import { TextEditor } from "../TextEditor";
import { Time } from "../Time";
import type { DoctypeField } from "./types";

/**
 * Render a human-readable value for a read-only field based on fieldtype.
 */
function renderReadOnlyValue(field: DoctypeField, value: any): string {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (field.fieldtype === "Check") {
    return value ? "✓" : "";
  }
  if (
    field.fieldtype === "Float" ||
    field.fieldtype === "Currency" ||
    field.fieldtype === "Percent"
  ) {
    const num = Number(value);
    if (isNaN(num)) return String(value);
    return field.fieldtype === "Currency"
      ? num.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : field.fieldtype === "Percent"
        ? `${num}%`
        : String(num);
  }
  if (field.fieldtype === "Int") {
    const num = Number(value);
    return isNaN(num) ? String(value) : String(Math.round(num));
  }
  if (field.fieldtype === "Date" && value) {
    try {
      const d = new Date(value);
      return d.toLocaleDateString();
    } catch {
      return String(value);
    }
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return String(value);
}

/**
 * Render an inline cell field, respecting Frappe field metadata:
 * - hidden === 1 => rendered inline but our caller should skip rendering the td
 * - read_only === 1 => show a plain text display (no editing)
 * - bold === 1 => bold label
 * - columns => width hint
 */
export const renderCellField = (
  field: DoctypeField,
  row: any,
  rowIndex: number,
  disabled: boolean,
  handleCellChange: (index: number, fieldname: string, val: any) => void,
) => {
  // Skip rendering entirely if hidden
  if (field.hidden === 1) return null;

  const isReadOnly = field.read_only === 1 || disabled;
  const rawValue = row[field.fieldname];
  const commonProps = {
    value: rawValue ?? field.default ?? "",
    onChange: (val: any) => handleCellChange(rowIndex, field.fieldname, val),
    disabled: isReadOnly,
    required: field.reqd === 1,
    label: "",
    placeholder: field.placeholder,
    className: "w-full",
  };

  const parseOptions = (options?: string) => {
    if (!options) return [];
    return options
      .split("\n")
      .map((opt: string) => ({ label: opt.trim(), value: opt.trim() }))
      .filter((o) => o.value !== "");
  };

  // For read-only fields, render as plain text
  if (isReadOnly || field.fieldtype === "Read Only") {
    return (
      <span
        className={cn(
          "inline-block w-full px-2 py-1 text-sm leading-5 truncate",
          field.bold === 1 ? "font-semibold" : "font-normal",
        )}
        title={renderReadOnlyValue(field, rawValue)}
      >
        {renderReadOnlyValue(field, rawValue) || (
          <span className="text-muted-foreground/40">—</span>
        )}
      </span>
    );
  }

  switch (field.fieldtype) {
    case "Barcode":
      return <Barcode {...commonProps} />;
    case "Button":
      return <ButtonField {...commonProps} label="" />;
    case "Check":
      return (
        <Check
          {...commonProps}
          value={rawValue || false}
          onChange={(val: boolean) =>
            handleCellChange(rowIndex, field.fieldname, val ? 1 : 0)
          }
        />
      );
    case "Code":
      return <Code {...commonProps} language="javascript" rows={4} />;
    case "Color":
      return <Color {...commonProps} />;
    case "Currency":
      return <Currency {...commonProps} value={rawValue || 0} />;
    case "Data":
      return <Data {...commonProps} />;
    case "Date":
      return <DateField {...commonProps} />;
    case "Datetime":
      return <Datetime {...commonProps} />;
    case "Duration":
      return <Duration {...commonProps} value={rawValue || 0} />;
    case "Dynamic Link":
      return (
        <DynamicLink
          {...commonProps}
          referenceDoctype={field.options as string}
          doctype={field.options as string}
        />
      );
    case "Float":
      return <Float {...commonProps} value={rawValue || 0} />;
    case "Geolocation":
      return <Geolocation {...commonProps} value={rawValue || null} />;
    case "Heading":
      return <Heading {...commonProps} level={2} />;
    case "HTML Editor":
      return <HTMLEditor {...commonProps} rows={4} />;
    case "Icon":
      return <Icon {...commonProps} />;
    case "Image":
      return <Image {...commonProps} value={rawValue || null} />;
    case "Int":
      return <Int {...commonProps} value={rawValue || 0} />;
    case "JSON":
      return <JSONField {...commonProps} value={rawValue || null} />;
    case "Link":
      return (
        <LinkField
          {...commonProps}
          doctype={field.options as string}
          referenceDoctype={field.options as string}
        />
      );
    case "Long Text":
      return <LongText {...commonProps} rows={3} />;
    case "Markdown Editor":
      return <MarkdownEditor {...commonProps} rows={4} />;
    case "Password":
      return <Password {...commonProps} showStrength={false} />;
    case "Percent":
      return <Percent {...commonProps} value={rawValue || 0} />;
    case "Phone":
      return <Phone {...commonProps} />;
    case "Rating":
      return <Rating {...commonProps} value={rawValue || 0} />;
    case "Select":
      return <Select {...commonProps} options={parseOptions(field.options)} />;
    case "Signature":
      return <Signature {...commonProps} value={rawValue || null} />;
    case "Small Text":
      return <SmallText {...commonProps} />;
    case "Table Multi Select":
    case "Table MultiSelect":
      return (
        <TableMultiSelect
          {...commonProps}
          doctype={field.options as string}
          value={rawValue || []}
          linkFieldname={field.linkFieldname}
        />
      );
    case "Text":
      return <Text {...commonProps} />;
    case "Text Editor":
      return <TextEditor {...commonProps} rows={4} />;
    case "Time":
      return <Time {...commonProps} />;
    default:
      return (
        <input
          type="text"
          disabled={isReadOnly}
          value={rawValue ?? ""}
          onChange={(e) =>
            handleCellChange(rowIndex, field.fieldname, e.target.value)
          }
          className={cn(
            "w-full bg-transparent px-2 py-1 text-sm rounded-xs outline-none focus-visible:bg-muted/50 transition-colors",
            field.bold === 1 && "font-semibold",
          )}
        />
      );
  }
};
