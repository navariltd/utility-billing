/**
 * Tones of the detail pages.
 *
 * Kept out of `status-pill.tsx` so that file only exports components (Fast
 * Refresh requirement) and so a tone can be reused without importing the pill.
 */

export type StatusTone =
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "primary"
  | "neutral";

/** Map a document status (Sales Invoice / Sales Order) to a pill tone. */
export function documentStatusTone(status?: string | null): StatusTone {
  switch (status) {
    case "Paid":
    case "Completed":
    case "Closed":
      return "success";
    case "Overdue":
    case "Cancelled":
      return "danger";
    case "Unpaid":
    case "Unbilled":
    case "To Bill":
    case "To Deliver and Bill":
      return "warning";
    case "Partly Paid":
    case "Partly Paid and Discounted":
    case "To Deliver":
      return "info";
    default:
      return "neutral";
  }
}

/** Label and tone of a meter reading, derived from its docstatus. */
export function readingStatus(docstatus?: number | null): {
  label: string;
  tone: StatusTone;
} {
  if (docstatus === 1) return { label: "Submitted", tone: "success" };
  if (docstatus === 2) return { label: "Cancelled", tone: "danger" };

  return { label: "Draft", tone: "warning" };
}
