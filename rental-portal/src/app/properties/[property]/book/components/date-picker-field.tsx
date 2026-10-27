/** A labelled date field backed by a popover calendar. */

"use client";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { CalendarDays, ChevronDown } from "lucide-react";
import { useState } from "react";
import type { Matcher } from "react-day-picker";
import { longDate, parseIsoDate, toIsoDate } from "./booking-dates";

interface DatePickerFieldProps {
  id?: string;
  label: string;
  value: string;
  onChange?: (value: string) => void;
  minDate?: string;
  maxDate?: string;
  hint?: string;
  disabled?: boolean;
  className?: string;
}

/** Date field with a popover calendar, min/max bounds and an optional hint. */
export function DatePickerField({
  id,
  label,
  value,
  onChange,
  minDate,
  maxDate,
  hint,
  disabled,
  className,
}: DatePickerFieldProps) {
  const [open, setOpen] = useState(false);
  const selected = parseIsoDate(value);
  const from = parseIsoDate(minDate);
  const to = parseIsoDate(maxDate);

  const disabledDays: Matcher[] = [];
  if (from) disabledDays.push({ before: from });
  if (to) disabledDays.push({ after: to });

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={id}>{label}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            type="button"
            variant="outline"
            disabled={disabled}
            className={cn(
              "h-11 w-full justify-start gap-2 px-3 text-left font-normal",
              !selected && "text-muted-foreground",
            )}
          >
            <CalendarDays className="text-muted-foreground h-4 w-4" />
            <span className="flex-1 truncate">{longDate(value)}</span>
            <ChevronDown className="text-muted-foreground h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            captionLayout="dropdown"
            selected={selected}
            defaultMonth={selected ?? from}
            disabled={disabledDays.length > 0 ? disabledDays : undefined}
            onSelect={(date) => {
              if (!date) return;
              onChange?.(toIsoDate(date));
              setOpen(false);
            }}
          />
        </PopoverContent>
      </Popover>
      {hint ? <p className="text-muted-foreground text-xs">{hint}</p> : null}
    </div>
  );
}
