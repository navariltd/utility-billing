"use client";

import { cn } from "@/lib/utils";

interface HTMLEditorProps {
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  rows?: number;
}

export const HTMLEditor = ({
  value = "",
  onChange,
  onBlur,
  placeholder = "Enter HTML content...",
  className = "",
  disabled = false,
  required = false,
  label,
  rows = 8,
}: HTMLEditorProps) => {
  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <label className="text-sm font-medium text-foreground flex items-center gap-0.5 select-none">
          {label}
          {required && (
            <span className="text-destructive font-bold text-red-500 ml-0.5">
              *
            </span>
          )}
        </label>
      )}
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        disabled={disabled}
        placeholder={placeholder}
        rows={rows}
        className={cn(
          "font-mono text-sm w-full rounded-md border border-input bg-background px-3 py-2 shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
      />
    </div>
  );
};
