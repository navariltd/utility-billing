"use client";

export interface TableProps {
  doctype: string;
  value: any[];
  onChange: (val: any[]) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  /** Number of leading columns to make sticky on the left. Defaults to 1. */
  stickyColumns?: number;
}

/**
 * Frappe DocField metadata – all fields as they come from the server.
 * Frappe uses 0/1 (number) for booleans.
 */
export interface DoctypeField {
  fieldname: string;
  label?: string;
  fieldtype: string;
  in_list_view?: 0 | 1;
  options?: string;
  reqd?: 0 | 1;
  default?: any;
  placeholder?: string;
  /** Frappe booleans (0/1) */
  hidden?: 0 | 1;
  read_only?: 0 | 1;
  collapsible?: 0 | 1;
  collapsible_depends_on?: string;
  depends_on?: string;
  show_on_timeline?: 0 | 1;
  bold?: 0 | 1;
  columns?: number;
  description?: string;
  allow_on_submit?: 0 | 1;
  ignore_user_permissions?: 0 | 1;
  print_hide?: 0 | 1;
  print_hide_if_no_value?: 0 | 1;
  unique?: 0 | 1;
  no_copy?: 0 | 1;
  set_only_once?: 0 | 1;
  permlevel?: number;
  translatable?: 0 | 1;
  hide_days?: 0 | 1;
  hide_seconds?: 0 | 1;
  non_negative?: 0 | 1;
  allow_in_quick_entry?: 0 | 1;
  search_index?: 0 | 1;
  in_global_search?: 0 | 1;
  in_filter?: 0 | 1;
  in_preview?: 0 | 1;
  in_standard_filter?: 0 | 1;
  allow_bulk_edit?: 0 | 1;
  ignore_xss_filter?: 0 | 1;
  remember_last_selected_value?: 0 | 1;
  hide_border?: 0 | 1;
  show_dashboard?: 0 | 1;
  is_virtual?: 0 | 1;
  sort_options?: 0 | 1;
  not_nullable?: 0 | 1;
  sticky?: 0 | 1;
  mask?: 0 | 1;
  show_description_on_click?: 0 | 1;
  make_attachment_public?: 0 | 1;
  fetch_if_empty?: 0 | 1;
  documentation_url?: string;
  link_filters?: string;
  max_height?: string;
  min_height?: string;
  alignment?: string;
  button_color?: string;
  [key: string]: any;
}

// ─── Form layout types for the detail modal ───
export interface FormField {
  fieldname: string;
  label: string;
  fieldtype: string;
  [key: string]: any;
}

export interface FormColumn {
  fields: FormField[];
}

export interface FormSection {
  label: string;
  columns: FormColumn[];
  /** Whether this section is collapsible */
  collapsible?: boolean;
  collapsed?: boolean;
}

export interface FormTab {
  label: string;
  sections: FormSection[];
}