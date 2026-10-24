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

export interface PaymentResult {
  payment_request: string;
  status: string;
  payment_url: string | null;
  channel: string;
  amount: number;
  outstanding_amount: number;
  currency: string | null;
  reference_doctype: string;
  reference_name: string;
}
