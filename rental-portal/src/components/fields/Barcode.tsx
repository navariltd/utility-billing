"use client";

import { cn } from "@/lib/utils";
import { Scan } from "lucide-react";
import * as React from "react";

interface BarcodeProps {
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
}

export const Barcode = ({
  value = "",
  onChange,
  onBlur,
  placeholder,
  className = "",
  disabled = false,
  required = false,
  label,
}: BarcodeProps) => {
  const inputRef = React.useRef<HTMLInputElement>(null);

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
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
          placeholder={placeholder}
          className={cn(
            "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            className,
          )}
        />
        <Scan className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
      </div>
    </div>
  );
};
