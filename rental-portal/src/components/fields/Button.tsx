"use client";

import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface ButtonFieldProps {
  value?: string;
  onChange?: (val: string) => void;
  onBlur?: () => void;
  className?: string;
  disabled?: boolean;
  label?: string;
  loading?: boolean;
  onClick?: () => void;
  variant?:
    | "default"
    | "destructive"
    | "outline"
    | "secondary"
    | "ghost"
    | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

export const ButtonField = ({
  value = "",
  onChange,
  onBlur,
  className = "",
  disabled = false,
  label = "Button",
  loading = false,
  onClick,
  variant = "default",
  size = "default",
}: ButtonFieldProps) => {
  const handleClick = () => {
    if (!disabled && !loading) {
      onClick?.();
      onChange?.(value);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      onBlur={onBlur}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
        variant === "default" &&
          "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        variant === "destructive" &&
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        variant === "outline" &&
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        variant === "secondary" &&
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        variant === "ghost" && "hover:bg-accent hover:text-accent-foreground",
        variant === "link" && "text-primary underline-offset-4 hover:underline",
        size === "default" && "h-9 px-4 py-2",
        size === "sm" && "h-8 rounded-md px-3 text-xs",
        size === "lg" && "h-10 rounded-md px-8",
        size === "icon" && "h-9 w-9",
        className,
      )}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {label}
    </button>
  );
};
