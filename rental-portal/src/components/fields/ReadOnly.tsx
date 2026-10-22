"use client";

import { cn } from "@/lib/utils";

interface ReadOnlyProps {
  value: any;
  onChange?: (val: any) => void;
  onBlur?: () => void;
  className?: string;
  label?: string;
  required?: boolean;
}

export const ReadOnly = ({
  value,
  onChange: _onChange,
  onBlur,
  className = "",
  label,
  required = false,
}: ReadOnlyProps) => {
  const displayValue = value?.toString() || "";

  return (
    <div
      className={cn("w-full flex flex-col gap-1.5", className)}
      onBlur={onBlur}
    >
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
      <div className="px-3 py-2 text-sm rounded-md bg-muted/30 border border-input min-h-[36px]">
        {displayValue || <span className="text-muted-foreground">Not set</span>}
      </div>
    </div>
  );
};
