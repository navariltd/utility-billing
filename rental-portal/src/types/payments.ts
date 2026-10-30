/**
 * Types for `utility_billing.api.portal.payments`.
 */

export interface PaymentGateway {
  name: string;
  label: string;
  gateway: string;
  company: string | null;
  channel: "Email" | "Phone" | "Other";
  currency: string | null;
  is_default: number;
  message: string | null;
}

export interface PaymentGatewaysPayload {
  gateways: PaymentGateway[];
  companies: string[];
}

export interface PayableInvoice {
  name: string;
  posting_date: string | null;
  due_date: string | null;
  grand_total: number;
  outstanding_amount: number;
  payable_amount: number;
  currency: string | null;
  status: string | null;
  customer: string;
  payable: boolean;
}

export interface PayableOrder {
  name: string;
  transaction_date: string | null;
  delivery_date: string | null;
  grand_total: number;
  advance_paid: number;
  per_billed: number | null;
  payable_amount: number;
  currency: string | null;
  status: string | null;
  customer: string;
  payable: boolean;
}

export interface CustomerDocuments {
  customer: string | null;
  customers: { name: string; customer_name: string }[];
  invoices: PayableInvoice[];
  orders: PayableOrder[];
  totals: {
    outstanding: Record<string, number>;
    advances: Record<string, number>;
  };
}

export interface DocumentLine {
  item_code: string;
  item_name: string | null;
  description: string | null;
  qty: number;
  uom: string | null;
  rate: number;
  amount: number;
}

export interface DocumentTax {
  description: string | null;
  charge_type: string | null;
  rate: number;
  tax_amount: number;
}

export interface DocumentMeterReading {
  item_code: string | null;
  meter_number: string | null;
  previous_reading: number | null;
  current_reading: number | null;
  uom: string | null;
  consumption: number | null;
  meter_reading: string | null;
}

/**
 * One invoice or order with the sections shown on its details page, returned
 * by `utility_billing.api.portal.payments.get_customer_document`.
 *
 * Invoices carry `posting_date`/`due_date`/`outstanding_amount`; orders carry
 * `transaction_date`/`delivery_date`/`advance_paid`.
 */
export interface CustomerDocumentDetail {
  doctype: "Sales Invoice" | "Sales Order";
  name: string;
  docstatus: number;
  customer: string;
  customer_name: string | null;
  status: string | null;
  company: string | null;
  currency: string | null;
  posting_date?: string | null;
  due_date?: string | null;
  transaction_date?: string | null;
  delivery_date?: string | null;
  net_total?: number;
  total_taxes_and_charges?: number;
  grand_total: number;
  rounded_total: number;
  paid_amount?: number;
  outstanding_amount?: number;
  advance_paid?: number;
  payable_amount: number;
  lines: DocumentLine[];
  taxes: DocumentTax[];
  meter_readings: DocumentMeterReading[];
}

/** Checkout link returned by `utility_billing.api.portal.payments.initiate_payment`. */
export interface PaymentLinkResult {
  payment_url: string | null;
  channel: string;
  amount: number;
  currency: string | null;
  payment_gateway: string;
  reference_doctype: string;
  reference_name: string;
}
