"use client";

import { cn } from "@/lib/utils";
import { Star } from "lucide-react";
import * as React from "react";

interface RatingProps {
  value: number;
  onChange: (val: number) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  max?: number;
}

export const Rating = ({
  value = 0,
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  max = 5,
}: RatingProps) => {
  const [hoveredValue, setHoveredValue] = React.useState<number | null>(null);

  const handleMouseEnter = (index: number) => {
    if (!disabled) {
      setHoveredValue(index);
    }
  };

  const handleMouseLeave = () => {
    setHoveredValue(null);
  };

  const handleClick = (index: number) => {
    if (!disabled) {
      onChange(index);
      onBlur?.();
    }
  };

  const displayValue = hoveredValue !== null ? hoveredValue : value;

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
      <div className="flex gap-0.5" onBlur={onBlur}>
        {Array.from({ length: max }, (_, i) => {
          const starValue = i + 1;
          const isFilled = starValue <= displayValue;
          return (
            <button
              key={i}
              type="button"
              onClick={() => handleClick(starValue)}
              onMouseEnter={() => handleMouseEnter(starValue)}
              onMouseLeave={handleMouseLeave}
              disabled={disabled}
              className={cn(
                "p-0.5 transition-all hover:scale-110",
                disabled && "cursor-not-allowed opacity-50",
              )}
            >
              <Star
                className={cn(
                  "size-6 transition-colors",
                  isFilled
                    ? "fill-yellow-500 text-yellow-500"
                    : "fill-muted text-muted",
                )}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
};
