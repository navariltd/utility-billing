"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as React from "react";

interface CurrencyProps {
  value: number;
  onChange: (val: number) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  currency?: string;
  decimals?: number;
  precision?: number;
  nonNegative?: boolean;
  min?: number;
  max?: number;
  length?: number;
}

export const Currency = ({
  value = 0,
  onChange,
  onBlur,
  placeholder = "0.00",
  className = "",
  disabled = false,
  required = false,
  label,
  currency = "$",
  decimals = 2,
  precision,
  nonNegative = false,
  min = -Infinity,
  max = Infinity,
  length,
}: CurrencyProps) => {
  const [displayValue, setDisplayValue] = React.useState(value.toString());

  const effectiveMin = nonNegative ? Math.max(min, 0) : min;
  const effectiveDecimals = precision !== undefined ? precision : decimals;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setDisplayValue(val);
    
    if (val === "" || val === "-" || val === "." || val === "-.") {
      onChange(0);
      return;
    }
    
    if (!/^-?\d*\.?\d*$/.test(val)) {
      return;
    }
    
    const num = parseFloat(val);
    if (!isNaN(num)) {
      const clamped = Math.min(Math.max(num, effectiveMin), max);
      const rounded = parseFloat(clamped.toFixed(effectiveDecimals));
      onChange(rounded);
    }
  };

  const handleBlur = () => {
    if (displayValue) {
      const num = parseFloat(displayValue);
      if (!isNaN(num)) {
        const clamped = Math.min(Math.max(num, effectiveMin), max);
        const formatted = clamped.toFixed(effectiveDecimals);
        setDisplayValue(formatted);
        onChange(clamped);
      }
    }
    onBlur?.();
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
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground z-10">
          {currency}
        </span>
        <Input
          type="text"
          value={displayValue}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={disabled}
          placeholder={placeholder}
          inputMode="decimal"
          maxLength={length}
          className={cn("pl-8", className)}
        />
      </div>
    </div>
  );
};