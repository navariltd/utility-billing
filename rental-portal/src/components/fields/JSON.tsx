"use client";

import { cn } from "@/lib/utils";
import * as React from "react";

interface JSONProps {
  value: any;
  onChange: (val: any) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  rows?: number;
}

export const JSON = ({
  value = null,
  onChange,
  onBlur,
  className = "",
  disabled = false,
  required = false,
  label,
  rows = 8,
}: JSONProps) => {
  const [text, setText] = React.useState(
    value ? globalThis.JSON.stringify(value, null, 2) : "",
  );
  const [error, setError] = React.useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setText(val);
    setError(null);

    if (val.trim() === "") {
      onChange(null);
      return;
    }

    try {
      const parsed = globalThis.JSON.parse(val);
      onChange(parsed);
    } catch (err) {
      setError("Invalid JSON format");
    }
  };

  const handleBlur = () => {
    if (text.trim() !== "") {
      try {
        const parsed = globalThis.JSON.parse(text);
        setText(globalThis.JSON.stringify(parsed, null, 2));
        onChange(parsed);
      } catch (err) {
        // Keep as is
      }
    }
    onBlur?.();
  };

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
      <textarea
        value={text}
        onChange={handleChange}
        onBlur={handleBlur}
        disabled={disabled}
        placeholder="Enter JSON..."
        rows={rows}
        className={cn(
          "font-mono text-sm w-full rounded-md border border-input bg-background px-3 py-2 shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          error && "border-destructive",
          className,
        )}
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
};
