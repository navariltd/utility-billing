"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as React from "react";

interface DurationProps {
  value: number;
  onChange: (val: number) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  hideDays?: boolean;
  hideSeconds?: boolean;
  length?: number;
}

export const Duration = ({
  value = 0,
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  hideDays: _hideDays,
  hideSeconds: _hideSeconds,
  length: _length,
}: DurationProps) => {
  const [hours, setHours] = React.useState(Math.floor(value / 3600));
  const [minutes, setMinutes] = React.useState(Math.floor((value % 3600) / 60));
  const [seconds, setSeconds] = React.useState(Math.floor(value % 60));

  const updateValue = (h: number, m: number, s: number) => {
    const total = h * 3600 + m * 60 + s;
    onChange(total);
  };

  const handleHourChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const h = parseInt(e.target.value) || 0;
    setHours(h);
    updateValue(h, minutes, seconds);
  };

  const handleMinuteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const m = parseInt(e.target.value) || 0;
    setMinutes(m);
    updateValue(hours, m, seconds);
  };

  const handleSecondChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const s = parseInt(e.target.value) || 0;
    setSeconds(s);
    updateValue(hours, minutes, s);
  };

  return (
    <div className={cn("w-full flex flex-col gap-1.5", className)}>
      {label && (
        <Label className="flex items-center gap-0.5 select-none">
          {label}
          {required && <span className="text-destructive ml-0.5">*</span>}
        </Label>
      )}
      <div className="flex gap-2">
        <div className="flex-1">
          <Input
            type="number"
            value={hours}
            onChange={handleHourChange}
            onBlur={onBlur}
            disabled={disabled}
            min={0}
          />
          <span className="text-xs text-muted-foreground mt-1 block">
            Hours
          </span>
        </div>
        <div className="flex-1">
          <Input
            type="number"
            value={minutes}
            onChange={handleMinuteChange}
            onBlur={onBlur}
            disabled={disabled}
            min={0}
            max={59}
          />
          <span className="text-xs text-muted-foreground mt-1 block">
            Minutes
          </span>
        </div>
        <div className="flex-1">
          <Input
            type="number"
            value={seconds}
            onChange={handleSecondChange}
            onBlur={onBlur}
            disabled={disabled}
            min={0}
            max={59}
          />
          <span className="text-xs text-muted-foreground mt-1 block">
            Seconds
          </span>
        </div>
      </div>
    </div>
  );
};
