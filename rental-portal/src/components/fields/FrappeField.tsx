"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Barcode } from "./Barcode";
import { Check } from "./Check";
import { ChildTable } from "./ChildTable";
import { Code } from "./Code";
import { Color } from "./Color";
import { Currency } from "./Currency";
import { Data } from "./Data";
import { Date } from "./Date";
import { Datetime } from "./Datetime";
import { Duration } from "./Duration";
import { DynamicLink } from "./DynamicLink";
import { Float } from "./Float";
import { Fold } from "./Fold";
import { Geolocation } from "./Geolocation";
import { HTMLEditor } from "./HTMLEditor";
import { Image } from "./Image";
import { Int } from "./Int";
import { JSON } from "./JSON";
import { LinkField } from "./LinkField";
import { LongText } from "./LongText";
import { MarkdownEditor } from "./MarkdownEditor";
import { Password } from "./Password";
import { Percent } from "./Percent";
import { Phone } from "./Phone";
import { Rating } from "./Rating";
import { ReadOnly } from "./ReadOnly";
import { Select } from "./Select";
import { Signature } from "./Signature";
import { SmallText } from "./SmallText";
import { Table } from "./Table";
import { TableMultiSelect } from "./TableMultiSelect";
import { TextEditor } from "./TextEditor";
import { Time } from "./Time";

export interface FrappeFieldMeta {
  fieldname: string;
  label?: string;
  fieldtype: string;
  options?: string | string[];
  default?: any;
  required?: boolean;
  read_only?: boolean;
  hidden?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  depends_on?: string;
  length?: number;
  precision?: number;
  unique?: boolean;
  in_list_view?: boolean;
  in_standard_filter?: boolean;
  in_global_search?: boolean;
  allow_in_quick_entry?: boolean;
  translatable?: boolean;
  no_copy?: boolean;
  set_only_once?: boolean;
  allow_bulk_edit?: boolean;
  ignore_user_permissions?: boolean;
  hidden_plaintext?: boolean;
  print_hide?: boolean;
  print_hide_if_no_value?: boolean;
  hide_before_desktop_breakpoint?: boolean;
  hide_display?: boolean;
  collapsible?: boolean;
  collapsed?: boolean;
  max_height?: string;
  min_height?: string;
  columns?: number;
  regex?: string;
  max_value?: number;
  min_value?: number;
  max_length?: number;
  min_length?: number;
  fetch_from?: string;
  scale?: number;
  non_negative?: boolean;
  read_only_depends_on?: string;
  bold?: boolean;
  allow_on_submit?: boolean;
  permlevel?: number;
  reqd?: boolean;
  remember_last_used_value?: boolean;
  sortable?: boolean;
  default_based_on?: string;
  [key: string]: any;
}

export interface FrappeFieldProps {
  field: FrappeFieldMeta;
  value?: any;
  onChange?: (value: any, fieldname?: string) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  showLabel?: boolean;
  doctype?: string;
  options?: string | string[];
  filters?: Record<string, any>;
  query?: string;
  referenceDoctype?: string;
  linkFieldname?: string;
  width?: number | string;
  rowIndex?: number;
  parentDoctype?: string;
  parentName?: string;
  [key: string]: any;
}

const getFieldType = (fieldtype: string): string => {
  const type = fieldtype.toLowerCase().replace(/\s+/g, " ");

  if (type.includes("data") || type === "text" || type === "small_text")
    return "data";
  if (type.includes("int") || type === "int") return "int";
  if (type.includes("float") || type === "float") return "float";
  if (type.includes("currency")) return "currency";
  if (type.includes("percent")) return "percent";
  if (type.includes("check") || type === "check") return "check";
  if (type.includes("select") && !type.includes("link")) return "select";
  if (type.includes("link")) return "link";
  if (type.includes("dynamic_link")) return "dynamic_link";
  if (type.includes("date")) return "date";
  if (type.includes("datetime")) return "datetime";
  if (type.includes("time")) return "time";
  if (type.includes("duration")) return "duration";
  if (type.includes("password")) return "password";
  if (type.includes("text") && type.includes("editor")) return "text_editor";
  if (type.includes("text") && type.includes("markdown"))
    return "markdown_editor";
  if (type.includes("text") && type.includes("html")) return "html_editor";
  if (type.includes("long_text") || type === "text") return "long_text";
  if (type.includes("small_text")) return "small_text";
  if (type.includes("phone") || type === "phone") return "phone";
  if (type.includes("email")) return "email";
  if (type.includes("url") || type === "url") return "url";
  if (type.includes("code")) return "code";
  if (type.includes("color")) return "color";
  if (type.includes("rating")) return "rating";
  if (type.includes("barcode")) return "barcode";
  if (type.includes("image")) return "image";
  if (type.includes("signature")) return "signature";
  if (type.includes("geolocation")) return "geolocation";
  if (type.includes("json")) return "json";
  if (type.includes("read_only") || type === "read_only") return "read_only";
  if (type.includes("button")) return "button";
  if (type.includes("heading")) return "heading";
  if (type.includes("fold")) return "fold";
  if (type.includes("table") && type.includes("multi"))
    return "table_multi_select";
  if (type.includes("table")) return "table";
  if (type.includes("child_table")) return "child_table";
  if (type.includes("section_break")) return "section_break";
  if (type.includes("column_break")) return "column_break";

  return "data";
};

const parseOptions = (
  options?: string | string[],
): { label: string; value: string }[] => {
  if (!options) return [];

  if (Array.isArray(options)) {
    return options.map((opt) => {
      if (typeof opt === "string") {
        return { label: opt, value: opt };
      }
      return opt;
    });
  }

  return options
    .split("\n")
    .map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return { label: "", value: "" };
      return { label: trimmed, value: trimmed };
    })
    .filter((opt) => opt.value !== "");
};

export const FrappeField = ({
  field,
  value,
  onChange,
  onBlur,
  className,
  disabled,
  showLabel = true,
  doctype,
  options: optionsProp,
  filters,
  query,
  referenceDoctype,
  linkFieldname,
  width,
  rowIndex,
  parentDoctype,
  parentName,
  ...props
}: FrappeFieldProps) => {
  const fieldType = getFieldType(field.fieldtype);
  const isRequired = !!(field.required || field.reqd);
  const isHidden = field.hidden;

  if (isHidden) return null;

  if (fieldType === "section_break") {
    return (
      <div className={cn("col-span-full my-4", className)}>
        <div className="border-t border-border" />
      </div>
    );
  }

  if (fieldType === "column_break") {
    return <div className={cn("w-full", className)} />;
  }

  if (fieldType === "heading") {
    return (
      <div className={cn("col-span-full", className)}>
        <h3 className="text-lg font-semibold">
          {field.label || field.fieldname}
        </h3>
        {field.description && (
          <p className="text-sm text-muted-foreground mt-1">
            {field.description}
          </p>
        )}
      </div>
    );
  }

  if (fieldType === "fold") {
    return (
      <Fold
        value={value}
        onChange={onChange}
        label={field.label || field.fieldname}
        className={className}
        disabled={disabled}
      >
        {value &&
          typeof value === "object" &&
          Object.keys(value).map((key) => {
            const nestedField: FrappeFieldMeta = {
              fieldname: key,
              fieldtype: "Data",
              label: key,
            };
            return (
              <FrappeField
                key={key}
                field={nestedField}
                value={value[key]}
                onChange={(val) => {
                  const newValue = { ...value, [key]: val };
                  onChange?.(newValue);
                }}
              />
            );
          })}
      </Fold>
    );
  }

  const commonProps = {
    value: value ?? field.default ?? "",
    onChange: (val: any) => onChange?.(val, field.fieldname),
    onBlur,
    label: showLabel ? field.label || field.fieldname : undefined,
    placeholder: field.placeholder,
    disabled: disabled || field.disabled,
    required: isRequired,
    description: field.description,
    className: cn(width && `w-[${width}px]`, className),
  };

  const renderField = () => {
    switch (fieldType) {
      case "data":
      case "email":
      case "url":
        return (
          <Data
            {...commonProps}
            type={
              fieldType === "email"
                ? "email"
                : fieldType === "url"
                  ? "url"
                  : "text"
            }
            maxLength={field.length}
            pattern={field.regex}
          />
        );

      case "int":
        return (
          <Int
            {...commonProps}
            min={field.min_value}
            max={field.max_value}
            nonNegative={field.non_negative}
          />
        );

      case "float":
        return (
          <Float
            {...commonProps}
            precision={field.precision}
            min={field.min_value}
            max={field.max_value}
            nonNegative={field.non_negative}
          />
        );

      case "currency":
        return (
          <Currency
            {...commonProps}
            precision={field.precision}
            currency={props.currency}
            min={field.min_value}
            max={field.max_value}
            nonNegative={field.non_negative}
          />
        );

      case "percent":
        return (
          <Percent
            {...commonProps}
            precision={field.precision}
            min={field.min_value}
            max={field.max_value}
            nonNegative={field.non_negative}
          />
        );

      case "check":
        return (
          <Check
            {...commonProps}
            value={!!value}
            onChange={(val) => onChange?.(val ? 1 : 0, field.fieldname)}
          />
        );

      case "select": {
        const selectOptions = parseOptions(optionsProp || field.options);
        return <Select {...commonProps} options={selectOptions} />;
      }

      case "link": {
        // For Link field, options is the target DocType (istable == 0)
        const linkDoctype =
          typeof field.options === "string" ? field.options : (doctype ?? "");
        return (
          <LinkField
            {...commonProps}
            doctype={linkDoctype || ""}
            filters={filters}
            query={query}
          />
        );
      }

      case "dynamic_link": {
        const refDoctype =
          referenceDoctype ||
          (typeof field.options === "string" ? field.options : "");
        return (
          <DynamicLink
            {...commonProps}
            doctype={parentDoctype || ""}
            referenceDoctype={refDoctype || ""}
            linkFieldname={linkFieldname}
            filters={filters}
          />
        );
      }

      case "date":
        return <Date {...commonProps} hideDays={field.hide_days} />;

      case "datetime":
        return (
          <Datetime
            {...commonProps}
            hideDays={field.hide_days}
            hideSeconds={field.hide_seconds}
          />
        );

      case "time":
        return <Time {...commonProps} hideSeconds={field.hide_seconds} />;

      case "duration":
        return (
          <Duration
            {...commonProps}
            hideDays={field.hide_days}
            hideSeconds={field.hide_seconds}
          />
        );

      case "password":
        return <Password {...commonProps} />;

      case "text_editor":
        return <TextEditor {...commonProps} />;

      case "markdown_editor":
        return <MarkdownEditor {...commonProps} />;

      case "html_editor":
        return <HTMLEditor {...commonProps} />;

      case "long_text":
      case "text":
        return <LongText {...commonProps} maxLength={field.length} rows={5} />;

      case "small_text":
        return <SmallText {...commonProps} maxLength={field.length} />;

      case "phone":
        return <Phone {...commonProps} mask={field.mask} />;

      case "code":
        return (
          <Code
            {...commonProps}
            language={typeof field.options === "string" ? field.options : ""}
          />
        );

      case "color":
        return <Color {...commonProps} />;

      case "rating":
        return <Rating {...commonProps} max={5} />;

      case "barcode":
        return <Barcode {...commonProps} value={value || ""} />;

      case "image":
        return <Image {...commonProps} value={value} />;

      case "signature":
        return <Signature {...commonProps} value={value} />;

      case "geolocation":
        return <Geolocation {...commonProps} value={value} />;

      case "json":
        return <JSON {...commonProps} value={value} />;

      case "read_only":
        return <ReadOnly {...commonProps} value={value} />;

      case "button":
        return (
          <div className={cn("flex flex-col gap-1.5", className)}>
            {showLabel && field.label && (
              <label className="text-sm font-medium text-foreground flex items-center gap-0.5 select-none">
                {field.label}
              </label>
            )}
            <Button
              type="button"
              onClick={() => props.onClick?.(field.fieldname)}
              disabled={commonProps.disabled}
              variant="default"
            >
              {field.label || field.fieldname}
            </Button>
          </div>
        );

      case "table": {
        // For Table field, options is the child DocType name (istable == 1)
        const tableDoctype =
          typeof field.options === "string" ? field.options : "";
        return <Table {...commonProps} doctype={tableDoctype} value={value} />;
      }

      case "child_table": {
        const childDoctype =
          typeof field.options === "string" ? field.options : "";
        return (
          <ChildTable {...commonProps} doctype={childDoctype} value={value} />
        );
      }

      case "table_multi_select": {
        const tableDoctype =
          typeof field.options === "string" ? field.options : "";
        return (
          <TableMultiSelect
            doctype={tableDoctype}
            value={value || []}
            onChange={(val) => onChange?.(val, field.fieldname)}
            disabled={disabled || field.disabled}
            required={isRequired}
            label={showLabel ? field.label || field.fieldname : undefined}
            placeholder={field.placeholder}
            className={cn(width && `w-[${width}px]`, className)}
            linkFieldname={field.linkFieldname}
            filters={filters}
            query={query}
          />
        );
      }

      default:
        return <Data {...commonProps} />;
    }
  };

  return (
    <div
      className={cn(
        "flex flex-col gap-1.5",
        width && `inline-block`,
        className,
      )}
      style={
        width
          ? { width: typeof width === "number" ? `${width}px` : width }
          : undefined
      }
    >
      {renderField()}
    </div>
  );
};

export default FrappeField;
