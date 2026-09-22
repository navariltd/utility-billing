"use client";

import { LinkField } from "./LinkField";

interface DynamicLinkProps {
  doctype: string;
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  clearable?: boolean;
  referenceDoctype?: string;
  linkFieldname?: string;
  query?: string;
  filters?: Record<string, any>;
  required?: boolean;
  label?: string;
}

export const DynamicLink = (props: DynamicLinkProps) => {
  return <LinkField {...props} />;
};
