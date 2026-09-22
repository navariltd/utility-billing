"use client";

import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

interface CheckProps {
  value: boolean;
  onChange: (val: boolean) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  length?: number;
}

export const Check = ({
  value = false,
  onChange,
  onBlur: _onBlur,
  placeholder: _placeholder,
  className = "",
  disabled = false,
  required = false,
  label,
  length: _length,
}: CheckProps) => {
  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      <div className="flex items-center gap-2">
        <Checkbox
          id="check-field"
          checked={value}
          onCheckedChange={(checked) => onChange(checked === true)}
          disabled={disabled}
        />
        {label && (
          <Label
            htmlFor="check-field"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer select-none"
          >
            {label}
            {required && <span className="text-destructive ml-0.5">*</span>}
          </Label>
        )}
      </div>
    </div>
  );
};
