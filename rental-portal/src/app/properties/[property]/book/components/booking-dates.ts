/**
 * Date helpers for the booking wizard.
 *
 * All values crossing the API boundary are `yyyy-MM-dd` strings; `Date` objects
 * are only used inside the date pickers.
 */

import {
  addDays,
  addMonths,
  differenceInCalendarDays,
  format,
  parseISO,
} from "date-fns";

/** Convert a date picker value to the ISO date string the API expects. */
export function toIsoDate(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

/** Parse an API date string, returning undefined for empty values. */
export function parseIsoDate(value?: string | null): Date | undefined {
  if (!value) return undefined;
  const date = parseISO(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

/** Add whole months to an ISO date. */
export function addMonthsToIso(value: string, months: number): string {
  return toIsoDate(addMonths(parseISO(value), months));
}

/** Add whole days to an ISO date. */
export function addDaysToIso(value: string, days: number): string {
  return toIsoDate(addDays(parseISO(value), days));
}

/** Number of calendar days between two ISO dates. */
export function daysBetween(start: string, end: string): number {
  return differenceInCalendarDays(parseISO(end), parseISO(start));
}

/** Long, human friendly date label. */
export function longDate(value?: string | null): string {
  const date = parseIsoDate(value);
  return date ? format(date, "EEE, d MMM yyyy") : "Not set";
}

/** Short month and year label used in summaries. */
export function monthLabel(value?: string | null): string {
  const date = parseIsoDate(value);
  return date ? format(date, "MMM yyyy") : "—";
}

/** The first day of the next month, as an ISO date. */
export function firstOfNextMonth(reference?: string | null): string {
  const date = reference ? parseISO(reference) : new Date();
  const next = new Date(date.getFullYear(), date.getMonth() + 1, 1);
  return toIsoDate(next);
}

/** Today, as an ISO date. */
export function todayIso(): string {
  return toIsoDate(new Date());
}
