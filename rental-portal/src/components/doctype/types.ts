/** Shared type definitions for DocType list and form components. */

export interface AppListColumn {
  fieldname: string;
  label: string;
  fieldtype: string;
  width?: number;
}

export interface ActiveFilter {
  value: string;
  operator: string;
  fieldtype: string;
}

export interface FilterItem {
  fieldname: string;
  operator: string;
  value: string;
  fieldtype: string;
}

export interface SectionGroup {
  section: FrappeFieldMeta | null;
  columns: FrappeFieldMeta[][];
}

export interface ColumnGroup {
  label: string;
  fieldname: string;
  fields: FrappeFieldMeta[];
}

export interface SectionGroupV2 {
  label: string;
  fieldname: string;
  collapsible: boolean;
  collapsed: boolean;
  columns: ColumnGroup[];
}

export interface TabConfig {
  label: string;
  fieldname: string;
  sections: SectionGroupV2[];
  show_dashboard?: number;
}

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

export const DOCSTATUS_MAP: Record<
  number,
  { label: string; variant: "default" | "secondary" | "outline" | "destructive" | "success" }
> = {
  0: { label: "Draft", variant: "secondary" },
  1: { label: "Submitted", variant: "success" },
  2: { label: "Cancelled", variant: "destructive" },
};

export interface WorkflowTransition {
  name: string;
  state: string;
  action: string;
  next_state: string;
  allowed: string;
  allow_self_approval: number;
  condition: string | null;
}