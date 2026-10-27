/**
 * Types for `utility_billing.api.portal.support`.
 *
 * Support tickets are ERPNext Issues linked to a property, and to the booking's
 * Utility Service Request when one exists. The detail payload carries the merged
 * conversation and status-change timeline.
 */

export type SupportIssueStatus = "Open" | "Replied" | "On Hold" | "Resolved" | "Closed";

export interface SupportIssue {
  name: string;
  subject: string;
  status: SupportIssueStatus;
  priority: string | null;
  issue_type: string | null;
  opening_date: string | null;
  creation: string | null;
  modified: string | null;
  resolution_time: number | string | null;
  first_responded_on: string | null;
  agreement_status: string | null;
  via_customer_portal: number;
  customer: string | null;
  customer_name: string | null;
  raised_by: string | null;
  property: string | null;
  service_request: string | null;
  is_open: boolean;
  snippet: string;
  description?: string;
  resolution_details?: string | null;
}

export interface SupportCounts {
  open: number;
  replied: number;
  resolved: number;
  total: number;
}

export interface SupportContext {
  name: string;
  reference: string;
  customer: string | null;
  customer_name: string | null;
  property: string | null;
  property_name: string | null;
  company: string | null;
  service_request: string | null;
}

export interface SupportPayload {
  context: SupportContext;
  issues: SupportIssue[];
  counts: SupportCounts;
}

export interface SupportTimelineEvent {
  id: string;
  type: "created" | "message" | "comment" | "status";
  date: string | null;
  author?: string | null;
  author_type?: "customer" | "support";
  subject?: string | null;
  content: string;
  field?: string;
  label?: string;
  old_value?: string | null;
  new_value?: string | null;
}

export interface SupportIssuePayload {
  issue: SupportIssue;
  timeline: SupportTimelineEvent[];
}
