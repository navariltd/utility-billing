/** Horizontal booking progress indicator with clickable completed steps. */

"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface BookingStep {
  label: string;
  description: string;
  icon: LucideIcon;
}

interface BookingStepperProps {
  steps: BookingStep[];
  current: number;
  onSelect?: (index: number) => void;
}

/** Stepper showing completed, current and upcoming steps. */
export function BookingStepper({
  steps,
  current,
  onSelect,
}: BookingStepperProps) {
  const progress = steps.length > 1 ? (current / (steps.length - 1)) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="bg-muted relative h-1.5 overflow-hidden rounded-full">
        <div
          className="bg-primary h-full rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <ol className="grid grid-cols-3 gap-2">
        {steps.map((step, index) => {
          const complete = index < current;
          const active = index === current;
          const Icon = step.icon;

          return (
            <li key={step.label}>
              <button
                type="button"
                disabled={!complete || !onSelect}
                onClick={() => onSelect?.(index)}
                className={cn(
                  "flex w-full items-center gap-2 rounded-xl p-2 text-left transition-colors",
                  complete && onSelect ? "cursor-pointer hover:bg-muted/60" : "",
                  active ? "bg-primary/5 ring-primary/20 ring-1" : "",
                )}
              >
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                    complete
                      ? "bg-primary text-primary-foreground border-primary"
                      : active
                        ? "border-primary text-primary bg-background"
                        : "text-muted-foreground bg-background",
                  )}
                >
                  {complete ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                </span>
                <span className="min-w-0">
                  <span
                    className={cn(
                      "block truncate text-sm font-medium",
                      !complete && !active && "text-muted-foreground",
                    )}
                  >
                    {step.label}
                  </span>
                  <span className="text-muted-foreground hidden truncate text-xs sm:block">
                    {step.description}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
