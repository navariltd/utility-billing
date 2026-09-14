/**
 * TableMultiSelectTypes – shared types for the TableMultiSelect component.
 *
 * Key dependencies: used by TableMultiSelect to define dropdown option shapes.
 */

import type * as React from "react";

/** A single option in the dropdown. */
export interface DropdownOption {
  label: string;
  value: string;
  extra?: any;
  description?: string;
  avatar?: string;
  icon?: React.ReactNode;
  metadata?: Record<string, any>;
}

/** Props for the TableMultiSelect component. */
export interface TableMultiSelectProps {
  doctype: string;
  value: string[];
  onChange: (val: string[]) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  placeholder?: string;
  linkFieldname?: string;
  filters?: Record<string, any>;
  query?: string;
  debounceDelay?: number;
  pageLength?: number;
}