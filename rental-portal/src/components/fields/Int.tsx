"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as React from "react";

interface IntProps {
  value: number;
  onChange: (val: number) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  min?: number;
  max?: number;
  step?: number;
  nonNegative?: boolean;
  precision?: number;
  length?: number;
}

export const Int = ({
  value = 0,
  onChange,
  onBlur,
  placeholder = "0",
  className = "",
  disabled = false,
  required = false,
  label,
  min = -Infinity,
  max = Infinity,
  step: _step = 1,
  nonNegative = false,
  precision: _precision,
  length,
}: IntProps) => {
  const [displayValue, setDisplayValue] = React.useState(
    value !== 0 ? value.toString() : "",
  );

  const effectiveMin = nonNegative ? Math.max(min, 0) : min;
  const effectiveMax = max;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    
    if (val === "" || val === "-") {
      setDisplayValue(val);
      onChange(0);
      return;
    }
    
    if (!/^-?\d+$/.test(val)) {
      return;
    }
    
    const num = parseInt(val, 10);
    if (!isNaN(num)) {
      const clamped = Math.min(Math.max(num, effectiveMin), effectiveMax);
      setDisplayValue(clamped.toString());
      onChange(clamped);
    }
  };

  const handleBlur = () => {
    if (displayValue) {
      const num = parseInt(displayValue);
      if (!isNaN(num)) {
        const clamped = Math.min(Math.max(num, effectiveMin), effectiveMax);
        setDisplayValue(clamped.toString());
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
      <Input
        type="text"
        value={displayValue}
        onChange={handleChange}
        onBlur={handleBlur}
        disabled={disabled}
        placeholder={placeholder}
        inputMode="numeric"
        maxLength={length}
      />
    </div>
  );
};
