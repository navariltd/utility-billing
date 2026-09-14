"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DataProps {
  value: any;
  onChange: (val: any) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  type?: "text" | "number" | "email" | "password" | "url";
  maxLength?: number;
  pattern?: string;
  length?: number;
}

export const Data = ({
  value = "",
  onChange,
  onBlur,
  placeholder,
  className = "",
  disabled = false,
  required = false,
  label,
  type = "text",
  maxLength,
  pattern,
  length,
}: DataProps) => {
  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <Label className="flex items-center gap-0.5 select-none">
          {label}
          {required && <span className="text-destructive ml-0.5">*</span>}
        </Label>
      )}
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        disabled={disabled}
        placeholder={placeholder}
        maxLength={maxLength || length}
        pattern={pattern}
        className={cn(className)}
      />
    </div>
  );
};