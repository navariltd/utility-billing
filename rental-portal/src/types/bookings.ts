/**
 * Types for `utility_billing.api.portal.bookings`.
 *
 * A booking is a submitted Utility Service Request; `lease_status` is derived
 * from its Contract and property allocations on the server.
 */

import type { PropertyDetails } from "./property-details";
import type { PortalCustomer } from "./portal";

export type LeaseStatus =
  | "Draft"
  | "Reserved"
  | "Contract Draft"
  | "Awaiting Signature"
  | "Active"
  | "Expired"
  | "Cancelled";

export type AllocationStatus = "Active" | "Upcoming" | "Expired" | "Released";

export interface BookingProperty {
  utility_property: string;
  property_name: string;
  item_code: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: number;
  allocation_status: AllocationStatus;
  cover_image: string | null;
  unit_number: string | null;
  location: string | null;
}

export interface BookingInvoice {
  name: string;
  posting_date: string | null;
  due_date: string | null;
  grand_total: number;
  outstanding_amount: number;
  currency: string | null;
  status: string | null;
  payable: boolean;
}

export interface BookingOrder {
  name: string;
  transaction_date: string | null;
  grand_total: number;
  advance_paid: number;
  per_billed: number | null;
  payable_amount: number;
  currency: string | null;
  status: string | null;
  payable: boolean;
}

export interface BookingDocuments {
  invoices: BookingInvoice[];
  orders: BookingOrder[];
}

export interface Booking {
  name: string;
  booking_reference: string;
  date: string | null;
  creation: string | null;
  start_date: string | null;
  end_date: string | null;
  contract_length_months: number | null;
  customer: string;
  customer_name: string | null;
  company: string | null;
  request_type: string | null;
  request_status: string | null;
  nrcpassport_no: string | null;
  notes: string;
  docstatus: number;
  lease_status: LeaseStatus;
  contract: string | null;
  contract_status: string | null;
  is_signed: number;
  properties: BookingProperty[];
  documents: BookingDocuments;
  can_modify: boolean;
  can_cancel: boolean;
  can_extend: boolean;
  can_pay: boolean;
  renewal_of?: string;
}

export interface BookingsPayload {
  customer: string | null;
  current: Booking[];
  history: Booking[];
  counts: { current: number; history: number };
}

export interface BookingTimelineEvent {
  label: string;
  date: string;
  type: string;
  by?: string | null;
}

export interface BookingDetailPayload {
  booking: Booking;
  timeline: BookingTimelineEvent[];
}

export interface BookingOptions {
  customer: PortalCustomer;
  property: PropertyDetails;
  price_list: string | null;
  currency: string | null;
  monthly_rent: number;
  deposit_amount: number;
  deposit_months: number;
  estimated_total: number;
  default_start_date: string;
  default_end_date: string;
  default_contract_length_months: number;
  service_item: string | null;
  pending_booking: string | null;
}
