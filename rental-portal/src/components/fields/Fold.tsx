"use client";

import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight } from "lucide-react";
import * as React from "react";

interface FoldProps {
  value?: any;
  onChange?: (val: any) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  label?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export const Fold = ({
  value: _value,
  onChange,
  onBlur,
  className = "",
  disabled = false,
  label = "Section",
  defaultOpen = false,
  children,
}: FoldProps) => {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  const toggle = () => {
    if (!disabled) {
      setIsOpen(!isOpen);
      onChange?.(!isOpen);
    }
  };

  return (
    <div className={cn("w-full border rounded-md overflow-hidden", className)}>
      <button
        type="button"
        onClick={toggle}
        disabled={disabled}
        className={cn(
          "flex items-center justify-between w-full px-4 py-3 bg-muted/20 hover:bg-muted/30 transition-colors text-left",
          disabled && "opacity-50 cursor-not-allowed",
        )}
        onBlur={onBlur}
      >
        <span className="font-medium text-sm">{label}</span>
        {isOpen ? (
          <ChevronDown className="size-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 text-muted-foreground" />
        )}
      </button>
      {isOpen && <div className="p-4">{children}</div>}
    </div>
  );
};
