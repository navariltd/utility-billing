/** Formatting helpers shared by the booking and payment pages. */

/** Format an amount in the given currency, falling back to a plain number. */
export function formatAmount(
  value: number | null | undefined,
  currency?: string | null,
): string {
  const amount = Number(value ?? 0);
  if (!currency) {
    return amount.toLocaleString();
  }

  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
}

/** Format a plain quantity (meter reading or consumption). */
export function formatNumber(
  value: number | null | undefined,
  fallback = "—",
): string {
  if (value === null || value === undefined) return fallback;

  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/** Format a date value, returning the fallback for empty values. */
export function formatDate(
  value?: string | null,
  fallback = "—",
): string {
  if (!value) return fallback;

  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Format a date and time value, returning the fallback for empty values. */
export function formatDateTime(
  value?: string | null,
  fallback = "—",
): string {
  if (!value) return fallback;

  return new Date(value).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
