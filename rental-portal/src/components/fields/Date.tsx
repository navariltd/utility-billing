"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Calendar } from "lucide-react";

interface DateProps {
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  min?: string;
  max?: string;
  hideDays?: boolean;
  hideSeconds?: boolean;
  length?: number;
}

export const Date = ({
  value = "",
  onChange,
  onBlur,
  placeholder = "YYYY-MM-DD",
  className = "",
  disabled = false,
  required = false,
  label,
  min,
  max,
  hideDays: _hideDays,
  hideSeconds: _hideSeconds,
  length,
}: DateProps) => {
  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <Label className="flex items-center gap-0.5 select-none">
          {label}
          {required && <span className="text-destructive ml-0.5">*</span>}
        </Label>
      )}
      <div className="relative">
        <Input
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
          placeholder={placeholder}
          min={min}
          max={max}
          maxLength={length}
          className={cn("[&::-webkit-calendar-picker-indicator]:opacity-50", className)}
        />
        <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
      </div>
    </div>
  );
};
