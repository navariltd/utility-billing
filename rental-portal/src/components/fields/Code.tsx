"use client";

import { cn } from "@/lib/utils";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

interface CodeProps {
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  language?: string;
  rows?: number;
  maxLength?: number;
  length?: number;
}

export const Code = ({
  value = "",
  onChange,
  onBlur,
  placeholder = "Enter code...",
  className = "",
  disabled = false,
  required = false,
  label,
  language: _language = "javascript",
  rows = 8,
  maxLength,
  length,
}: CodeProps) => {
  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <Label className="flex items-center gap-0.5 select-none">
          {label}
          {required && <span className="text-destructive ml-0.5">*</span>}
        </Label>
      )}
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        disabled={disabled}
        placeholder={placeholder}
        rows={rows}
        maxLength={maxLength || length}
        className={cn("font-mono text-sm", className)}
      />
    </div>
  );
};