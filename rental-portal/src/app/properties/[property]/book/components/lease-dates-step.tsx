/** First booking step: move-in date, contract length and cost preview. */

"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from "@/components/ui/input-group";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { formatAmount } from "@/lib/format";
import type { BookingOptions } from "@/types/bookings";
import { CalendarRange, Coins, Info, Wallet } from "lucide-react";
import { useMemo } from "react";
import {
  addDaysToIso,
  addMonthsToIso,
  daysBetween,
  firstOfNextMonth,
  longDate,
} from "./booking-dates";
import { DatePickerField } from "./date-picker-field";

const CONTRACT_LENGTHS = [3, 6, 12, 24, 36];

interface LeaseDatesStepProps {
  options: BookingOptions;
  startDate: string;
  endDate: string;
  months: number;
  customEnd: boolean;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string | null) => void;
  onMonthsChange: (value: number) => void;
}

/** Advanced date and contract-length selection with a live cost preview. */
export function LeaseDatesStep({
  options,
  startDate,
  endDate,
  months,
  customEnd,
  onStartDateChange,
  onEndDateChange,
  onMonthsChange,
}: LeaseDatesStepProps) {
  const rent = options.monthly_rent;
  const deposit = options.deposit_amount;
  const minimumStart = options.default_start_date;

  const presets = useMemo(
    () => [
      { label: "Earliest move-in", value: minimumStart },
      { label: "1st of next month", value: firstOfNextMonth(minimumStart) },
      { label: "In 2 weeks", value: addDaysToIso(minimumStart, 14) },
    ],
    [minimumStart],
  );

  const nights = startDate && endDate ? daysBetween(startDate, endDate) : 0;
  const totalRent = rent * months;
  const dueAtMoveIn = rent + deposit;
  const isPresetLength = CONTRACT_LENGTHS.includes(months);

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold">Move-in date</h3>
            <p className="text-muted-foreground text-xs">
              Pick the day the tenancy should start.
            </p>
          </div>
          <Badge variant="secondary" className="gap-1">
            <CalendarRange className="h-3 w-3" />
            {nights > 0 ? `${nights} days` : "Choose dates"}
          </Badge>
        </div>

        <div className="flex flex-wrap gap-2">
          {presets.map((preset) => (
            <Button
              key={preset.label}
              type="button"
              size="sm"
              variant={startDate === preset.value ? "default" : "outline"}
              className="cursor-pointer rounded-full"
              onClick={() => onStartDateChange(preset.value)}
            >
              {preset.label}
            </Button>
          ))}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <DatePickerField
            id="lease-start"
            label="Lease start"
            value={startDate}
            minDate={minimumStart}
            maxDate={addMonthsToIso(minimumStart, 24)}
            hint="The earliest available move-in date."
            onChange={onStartDateChange}
          />
          <DatePickerField
            id="lease-end"
            label="Lease end"
            value={endDate}
            minDate={startDate ? addDaysToIso(startDate, 1) : minimumStart}
            maxDate={startDate ? addMonthsToIso(startDate, 60) : undefined}
            hint={
              customEnd
                ? "Custom end date. Pick a contract length to reset it."
                : "Calculated from the contract length."
            }
            onChange={(value) => onEndDateChange(value)}
          />
        </div>

        {customEnd ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="cursor-pointer px-0"
            onClick={() => onEndDateChange(null)}
          >
            Reset to contract length
          </Button>
        ) : null}
      </section>

      <Separator />

      <section className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold">Contract length</h3>
          <p className="text-muted-foreground text-xs">
            Longer tenancies lock in the same monthly rent.
          </p>
        </div>

        <ToggleGroup
          type="single"
          variant="outline"
          className="grid w-full grid-cols-5"
          value={isPresetLength ? String(months) : ""}
          onValueChange={(value) => {
            if (value) onMonthsChange(Number(value));
          }}
        >
          {CONTRACT_LENGTHS.map((length) => (
            <ToggleGroupItem
              key={length}
              value={String(length)}
              aria-label={`${length} months`}
              className="h-auto flex-col gap-0.5 py-2"
            >
              <span className="text-sm font-semibold">{length}</span>
              <span className="text-muted-foreground text-[10px]">months</span>
            </ToggleGroupItem>
          ))}
        </ToggleGroup>

        <div className="flex flex-wrap items-end gap-3">
          <div className="w-40 space-y-2">
            <Label htmlFor="custom-months">Custom length</Label>
            <InputGroup>
              <InputGroupInput
                id="custom-months"
                type="number"
                min={1}
                max={60}
                value={months}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  if (Number.isFinite(value) && value > 0) onMonthsChange(value);
                }}
              />
              <InputGroupAddon align="inline-end">
                <InputGroupText>months</InputGroupText>
              </InputGroupAddon>
            </InputGroup>
          </div>
          <p className="text-muted-foreground pb-2 text-xs">
            {longDate(startDate)} → {longDate(endDate)}
          </p>
        </div>
      </section>

      <div className="bg-muted/40 grid gap-4 rounded-xl border p-4 sm:grid-cols-3">
        <div className="flex items-start gap-2">
          <Wallet className="text-muted-foreground mt-0.5 h-4 w-4" />
          <div>
            <p className="text-muted-foreground text-xs">Monthly rent</p>
            <p className="font-semibold">
              {formatAmount(rent, options.currency)}
            </p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Coins className="text-muted-foreground mt-0.5 h-4 w-4" />
          <div>
            <p className="text-muted-foreground text-xs">
              Deposit ({options.deposit_months}{" "}
              {options.deposit_months === 1 ? "month" : "months"})
            </p>
            <p className="font-semibold">
              {formatAmount(deposit, options.currency)}
            </p>
          </div>
        </div>
        <div>
          <p className="text-muted-foreground text-xs">
            Rent for {months} {months === 1 ? "month" : "months"}
          </p>
          <p className="font-semibold">
            {formatAmount(totalRent, options.currency)}
          </p>
        </div>
      </div>

      <div className="border-primary/20 bg-primary/5 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-dashed px-4 py-3">
        <span className="flex items-center gap-2 text-sm">
          <Info className="text-primary h-4 w-4" />
          Due at move-in (first month + deposit)
        </span>
        <span className="text-lg font-semibold">
          {formatAmount(dueAtMoveIn, options.currency)}
        </span>
      </div>
    </div>
  );
}
