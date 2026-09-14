"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as React from "react";

interface PercentProps {
  value: number;
  onChange: (val: number) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  min?: number;
  max?: number;
  step?: number;
  decimals?: number;
  precision?: number;
  nonNegative?: boolean;
  length?: number;
}

export const Percent = ({
  value = 0,
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  min = 0,
  max = 100,
  step: _step = 1,
  decimals = 0,
  precision,
  nonNegative = false,
  length,
}: PercentProps) => {
  const [displayValue, setDisplayValue] = React.useState(
    value !== 0 ? value.toString() : "",
  );

  const effectiveMin = nonNegative ? Math.max(min, 0) : min;
  const effectiveMax = max;
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
      const clamped = Math.min(Math.max(num, effectiveMin), effectiveMax);
      const rounded = parseFloat(clamped.toFixed(effectiveDecimals));
      onChange(rounded);
    }
  };

  const handleBlur = () => {
    if (displayValue) {
      const num = parseFloat(displayValue);
      if (!isNaN(num)) {
        const clamped = Math.min(Math.max(num, effectiveMin), max);
        setDisplayValue(clamped.toFixed(effectiveDecimals));
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
        <Input
          type="text"
          value={displayValue}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={disabled}
          placeholder="0"
          inputMode="decimal"
          maxLength={length}
          className={cn("pr-8", className)}
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
          %
        </span>
      </div>
    </div>
  );
};