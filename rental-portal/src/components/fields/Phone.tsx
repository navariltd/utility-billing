"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as React from "react";

interface PhoneProps {
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  countryCode?: string;
  mask?: boolean;
  length?: number;
}

export const Phone = ({
  value = "",
  onChange,
  onBlur,
  placeholder = "+1 234 567 8900",
  className = "",
  disabled = false,
  required = false,
  label,
  countryCode = "+1",
  mask: _mask,
  length,
}: PhoneProps) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const digits = raw.replace(/\D/g, "");

    const trimmed = digits.slice(0, 15);

    onChange(trimmed);
  };

  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <Label className="flex items-center gap-0.5 select-none">
          {label}
          {required && <span className="text-destructive ml-0.5">*</span>}
        </Label>
      )}
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground z-10">
          {countryCode}
        </span>
        <Input
          type="tel"
          value={value}
          onChange={handleChange}
          onBlur={onBlur}
          disabled={disabled}
          placeholder={placeholder}
          maxLength={length}
          className={cn("pl-12", className)}
        />
      </div>
    </div>
  );
};
