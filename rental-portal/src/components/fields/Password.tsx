"use client";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff } from "lucide-react";
import * as React from "react";

interface PasswordProps {
  value: string;
  onChange: (val: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  showStrength?: boolean;
  length?: number;
}

export const Password = ({
  value = "",
  onChange,
  onBlur,
  placeholder = "Enter password...",
  className = "",
  disabled = false,
  required = false,
  label,
  showStrength = true,
  length,
}: PasswordProps) => {
  const [showPassword, setShowPassword] = React.useState(false);

  const getStrength = (password: string): { score: number; label: string } => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;
    return {
      score,
      label: ["Weak", "Fair", "Good", "Strong", "Very Strong"][score] || "",
    };
  };

  const strength = getStrength(value);
  const strengthColors = [
    "bg-red-500",
    "bg-orange-500",
    "bg-yellow-500",
    "bg-green-500",
    "bg-green-600",
  ];

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
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
          placeholder={placeholder}
          maxLength={length}
          className={cn("pr-10", className)}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
        >
          {showPassword ? (
            <EyeOff className="size-4" />
          ) : (
            <Eye className="size-4" />
          )}
        </button>
      </div>
      {showStrength && value && (
        <div className="space-y-1">
          <div className="flex gap-1">
            {[0, 1, 2, 3, 4].map((index) => (
              <div
                key={index}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  index < strength.score
                    ? strengthColors[strength.score - 1]
                    : "bg-muted",
                )}
              />
            ))}
          </div>
          <p className="text-xs text-muted-foreground">{strength.label}</p>
        </div>
      )}
    </div>
  );
};