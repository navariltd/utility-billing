/**
 * Types for the property details payload returned by
 * `utility_billing.api.portal.property_details.get_property_details`.
 */

import type { TenantProperty } from "@/types/portal";

export interface PropertyFeatureItem {
  feature: string;
  feature_type?: string | null;
  notes?: string | null;
}

export interface PropertyGalleryItem {
  image: string;
  title?: string | null;
  description?: string | null;
}

/** Descriptive property fields (no asset or purchase information). */
export interface PropertyDetails {
  name: string;
  property_name: string;
  utility_category: string | null;
  company: string | null;
  status: string | null;
  location: string | null;
  territory: string | null;
  house_no: string | null;
  plot_no: string | null;
  unit_number: string | null;
  unit_type: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  unit_size: number | null;
  floor_level: string | null;
  cover_image: string | null;
  parent_utility_property: string | null;
  is_group: number;
  lot_size: string | null;
  unique_features: string | null;
  legal_description: string | null;
  features: PropertyFeatureItem[];
  image_gallery: PropertyGalleryItem[];
}

export interface MeterReadingRow {
  name: string;
  date: string | null;
  customer: string;
  company: string | null;
  docstatus: number;
}

export interface ServiceRequestRow {
  name: string;
  date: string | null;
  request_type: string | null;
  request_status: string | null;
  customer: string;
}

export interface SalesInvoiceRow {
  name: string;
  posting_date: string | null;
  due_date: string | null;
  grand_total: number;
  outstanding_amount: number;
  status: string | null;
  docstatus: number;
  currency: string | null;
  customer: string;
}

export interface SalesOrderRow {
  name: string;
  transaction_date: string | null;
  delivery_date: string | null;
  grand_total: number;
  status: string | null;
  docstatus: number;
  currency: string | null;
  customer: string;
}

export interface PaymentEntryRow {
  name: string;
  posting_date: string | null;
  payment_type: string | null;
  mode_of_payment: string | null;
  paid_amount: number;
  received_amount: number;
  paid_from_account_currency: string | null;
  paid_to_account_currency: string | null;
  reference_no: string | null;
  status: string | null;
  docstatus: number;
  party: string;
}

/** Documents the caller is allowed to see for their own property. */
export interface PropertyDocuments {
  meter_readings: MeterReadingRow[];
  service_requests: ServiceRequestRow[];
  sales_invoices: SalesInvoiceRow[];
  sales_orders: SalesOrderRow[];
  payment_entries: PaymentEntryRow[];
  totals: {
    invoiced: number;
    outstanding: number;
    paid: number;
    currency: string | null;
  };
}

/** Tenancy of the caller for the requested property (current or past). */
export interface PropertyTenancy extends TenantProperty {
  is_current: boolean;
}

export interface PropertyDetailsPayload {
  property: PropertyDetails;
  tenancy: PropertyTenancy | null;
  is_mine: boolean;
  is_available: boolean;
  can_book: boolean;
  documents: PropertyDocuments | null;
}
