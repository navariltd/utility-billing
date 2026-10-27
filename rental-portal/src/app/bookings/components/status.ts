/** Status badge tones for bookings and property allocations. */

import type { PropertyStatusTone } from "@/components/properties";
import type { AllocationStatus, LeaseStatus } from "@/types/bookings";

const LEASE_TONES: Record<LeaseStatus, PropertyStatusTone> = {
  Draft: "neutral",
  Reserved: "reserved",
  "Contract Draft": "reserved",
  "Awaiting Signature": "maintenance",
  Active: "available",
  Expired: "history",
  Cancelled: "history",
};

export function leaseTone(status: LeaseStatus | string): PropertyStatusTone {
  return LEASE_TONES[status as LeaseStatus] ?? "neutral";
}

const LEASE_LABELS: Partial<Record<LeaseStatus, string>> = {
  Draft: "Pending review",
};

/** Portal label of a lease status; drafts are awaiting manager confirmation. */
export function leaseLabel(status: LeaseStatus | string): string {
  return LEASE_LABELS[status as LeaseStatus] ?? status;
}

const ALLOCATION_TONES: Record<AllocationStatus, PropertyStatusTone> = {
  Active: "available",
  Upcoming: "reserved",
  Expired: "history",
  Released: "history",
};

export function allocationTone(status: AllocationStatus): PropertyStatusTone {
  return ALLOCATION_TONES[status] ?? "neutral";
}
