/** Utility functions for DocTypeList and DocTypeForm components. */

import type { FrappeFieldMeta, TabConfig, SectionGroupV2, ColumnGroup } from "./types";

export const QUICK_DATE_RANGES = [
  { label: "1h", value: "1h", minutes: 60 },
  { label: "6h", value: "6h", minutes: 360 },
  { label: "24h", value: "24h", minutes: 1440 },
  { label: "7d", value: "7d", minutes: 10080 },
  { label: "30d", value: "30d", minutes: 43200 },
  { label: "90d", value: "90d", minutes: 129600 },
  { label: "1y", value: "1y", minutes: 525600 },
];

export const OPERATOR_OPTIONS: Record<string, { value: string; label: string }[]> = {
  text: [
    { value: "=", label: "Equals" },
    { value: "like", label: "Contains" },
    { value: "__starts_with", label: "Starts With" },
    { value: "__ends_with", label: "Ends With" },
  ],
  numeric: [
    { value: "=", label: "Equals" },
    { value: ">", label: "Greater Than" },
    { value: "<", label: "Less Than" },
    { value: ">=", label: "Greater or Equal" },
    { value: "<=", label: "Less or Equal" },
  ],
  exact: [{ value: "=", label: "Equals" }],
  date: [
    { value: "=", label: "Equals" },
    { value: ">", label: "After" },
    { value: "<", label: "Before" },
    { value: ">=", label: "On or After" },
    { value: "<=", label: "On or Before" },
  ],
};

/** Format a cell value for display based on fieldtype. */
export function formatCellValue(value: any, fieldtype: string): string {
  if (value === null || value === undefined || value === "") return "—";
  switch (fieldtype) {
    case "Currency":
    case "Float":
    case "Percent":
      return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    case "Date":
      return typeof value === "string" && value.length >= 10 ? value.slice(0, 10) : String(value);
    case "Check":
      return value ? "✓" : "—";
    case "Select":
      return String(value).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    default:
      return String(value);
  }
}

/** Convert a date string to a human-friendly relative time label. */
export function timeAgo(dateStr: string): string {
  if (!dateStr) return "—";
  const now = Date.now();
  const d = new Date(dateStr).getTime();
  const diffMs = now - d;
  if (diffMs < 0) return "0M";
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "0M";
  if (mins < 60) return `${mins}M`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}H`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}D`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}M`;
  const years = Math.floor(months / 12);
  return `${years}Y`;
}

/** Get operator options appropriate for a given fieldtype. */
export function getOperatorsForFieldtype(fieldtype: string): { value: string; label: string }[] {
  switch (fieldtype) {
    case "Currency":
    case "Float":
    case "Int":
    case "Percent":
    case "Duration":
      return OPERATOR_OPTIONS.numeric;
    case "Date":
    case "Datetime":
      return OPERATOR_OPTIONS.date;
    case "Select":
    case "Link":
    case "Check":
      return OPERATOR_OPTIONS.exact;
    default:
      return OPERATOR_OPTIONS.text;
  }
}

/** Get appropriate HTML input type for a given fieldtype. */
export function getInputTypeForFieldtype(fieldtype: string): string {
  switch (fieldtype) {
    case "Currency":
    case "Float":
    case "Int":
    case "Percent":
      return "number";
    case "Date":
      return "date";
    case "Datetime":
      return "datetime-local";
    case "Check":
      return "checkbox";
    default:
      return "text";
  }
}

/** Extract Tab Break fields from schema fields to build the tab list. */
export function generateTabList(
  fields: FrappeFieldMeta[],
): { label: string; fieldname: string; show_dashboard: number; is_default?: boolean }[] {
  if (!fields || !Array.isArray(fields)) return [];

  const tabs: { label: string; fieldname: string; show_dashboard: number; is_default?: boolean }[] = [];
  const hasTabBreaks = fields.some((f) => f.fieldtype === "Tab Break");

  if (hasTabBreaks) {
    // Create a default tab for leading fields before the first Tab Break
    if (fields[0]?.fieldtype !== "Tab Break") {
      tabs.push({ label: "Details", fieldname: "tab_default_details", show_dashboard: 0, is_default: true });
    }

    fields.forEach((field) => {
      if (field.fieldtype === "Tab Break") {
        tabs.push({
          label: field.label || field.fieldname,
          fieldname: field.fieldname,
          show_dashboard: (field as any).show_dashboard || 0,
        });
      }
    });
  } else {
    // No Tab Breaks — create a single default tab with all fields (section breaks work within it)
    tabs.push({ label: "Details", fieldname: "tab_all", show_dashboard: 0, is_default: true });
  }

  return tabs;
}

/** Returns sections/columns/fields for fields belonging to a given tab. */
export function getFieldsForTab(
  fields: FrappeFieldMeta[],
  currentTab: { fieldname: string; is_default?: boolean },
): SectionGroupV2[] {
  if (!fields || !Array.isArray(fields)) return [];

  const sections: SectionGroupV2[] = [];
  let currentSection: SectionGroupV2 | null = null;
  let currentColumn: ColumnGroup | null = null;

  if (currentTab?.is_default) {
    for (const field of fields) {
      if (field.fieldtype === "Tab Break") break;
      if (field.fieldtype === "Section Break") {
        currentSection = {
          label: field.label || "",
          fieldname: field.fieldname,
          collapsible: (field as any).collapsible === 1 || false,
          collapsed: (field as any).collapsed === 1 || false,
          columns: [],
        };
        sections.push(currentSection);
        currentColumn = null;
        continue;
      }
      if (field.fieldtype === "Column Break") {
        if (!currentSection) {
          currentSection = { label: "", fieldname: `section_${Math.random().toString(36).substring(2, 6)}`, collapsible: false, collapsed: false, columns: [] };
          sections.push(currentSection);
        }
        currentColumn = { label: field.label || "", fieldname: field.fieldname, fields: [] };
        currentSection.columns.push(currentColumn);
        continue;
      }
      if (["Fold", "Page Break"].includes(field.fieldtype)) continue;
      if (field.hidden) continue;
      if (!currentSection) {
        currentSection = { label: "", fieldname: `section_${Math.random().toString(36).substring(2, 6)}`, collapsible: false, collapsed: false, columns: [] };
        sections.push(currentSection);
      }
      if (!currentColumn) {
        currentColumn = { label: "", fieldname: `column_${Math.random().toString(36).substring(2, 6)}`, fields: [] };
        currentSection.columns.push(currentColumn);
      }
      currentColumn.fields.push(field);
    }
    return sections.filter((sec) => {
      sec.columns = sec.columns.filter((col) => col.fields.length > 0);
      return sec.columns.length > 0;
    });
  }

  const tabNames = fields.filter((f) => f.fieldtype === "Tab Break").map((f) => f.fieldname);
  const tabIdx = tabNames.indexOf(currentTab?.fieldname || "");
  if (tabIdx < 0) return [];

  let captureActive = false;
  let tabBreaksSeen = 0;

  fields.forEach((field) => {
    if (field.fieldtype === "Tab Break") {
      if (tabBreaksSeen === tabIdx) {
        captureActive = true;
      } else if (tabBreaksSeen > tabIdx) {
        captureActive = false;
      }
      tabBreaksSeen++;
      return;
    }

    if (!captureActive) return;

    if (field.fieldtype === "Section Break") {
      currentSection = {
        label: field.label || "",
        fieldname: field.fieldname,
        collapsible: (field as any).collapsible === 1 || false,
        collapsed: (field as any).collapsed === 1 || false,
        columns: [],
      };
      sections.push(currentSection);
      currentColumn = null;
      return;
    }

    if (field.fieldtype === "Column Break") {
      if (!currentSection) {
        currentSection = { label: "", fieldname: `section_${Math.random().toString(36).substring(2, 6)}`, collapsible: false, collapsed: false, columns: [] };
        sections.push(currentSection);
      }
      currentColumn = { label: field.label || "", fieldname: field.fieldname, fields: [] };
      currentSection.columns.push(currentColumn);
      return;
    }

    if (["Fold", "Page Break"].includes(field.fieldtype)) return;
    if (field.hidden) return;

    if (!currentSection) {
      currentSection = { label: "", fieldname: `section_${Math.random().toString(36).substring(2, 6)}`, collapsible: false, collapsed: false, columns: [] };
      sections.push(currentSection);
    }
    if (!currentColumn) {
      currentColumn = { label: "", fieldname: `column_${Math.random().toString(36).substring(2, 6)}`, fields: [] };
      currentSection.columns.push(currentColumn);
    }

    currentColumn.fields.push(field);
  });

  return sections.filter((sec) => {
    sec.columns = sec.columns.filter((col) => col.fields.length > 0);
    return sec.columns.length > 0;
  });
}

/** Build tabs with their full field data. Combines generateTabList + getFieldsForTab. */
export function buildTabs(fields: FrappeFieldMeta[]): TabConfig[] {
  const tabMeta = generateTabList(fields);
  return tabMeta.map((tab) => ({
    ...tab,
    sections: getFieldsForTab(fields, tab),
  }));
}

/** Get the default tab from a list of tabs, respecting URL hash. */
export function getDefaultTab(tabs: TabConfig[]): string {
  if (tabs.length === 0) return "";
  const hash = window.location.hash.replace("#", "");
  if (hash) {
    const match = tabs.find((t) => t.fieldname === hash || t.label.toLowerCase() === hash);
    if (match) return match.fieldname;
  }
  return tabs[0].fieldname;
}