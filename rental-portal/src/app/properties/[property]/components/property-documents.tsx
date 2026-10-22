/**
 * Related documents of a property the user is linked to.
 *
 * Renders the Sales Invoices, Sales Orders, Payment Entries, Meter Readings and
 * Utility Service Requests returned by
 * `utility_billing.api.portal.property_details.get_property_details`.
 */

"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { PropertyDocuments } from "@/types/property-details";
import {
  DocumentTable,
  formatDate,
  formatDocstatus,
  type DocumentColumn,
} from "./document-table";
import { formatAmount } from "./property-side-panel";

interface TabDefinition {
  value: string;
  label: string;
  rows: any[];
  columns: DocumentColumn<any>[];
  emptyMessage: string;
}

const invoiceColumns: DocumentColumn<any>[] = [
  { label: "Date", render: (row) => formatDate(row.posting_date) },
  { label: "Invoice", render: (row) => row.name },
  { label: "Due", render: (row) => formatDate(row.due_date) },
  {
    label: "Total",
    align: "right",
    render: (row) => formatAmount(row.grand_total, row.currency),
  },
  {
    label: "Outstanding",
    align: "right",
    render: (row) => formatAmount(row.outstanding_amount, row.currency),
  },
  { label: "Status", render: (row) => row.status || formatDocstatus(row.docstatus) },
];

const orderColumns: DocumentColumn<any>[] = [
  { label: "Date", render: (row) => formatDate(row.transaction_date) },
  { label: "Order", render: (row) => row.name },
  { label: "Delivery", render: (row) => formatDate(row.delivery_date) },
  {
    label: "Total",
    align: "right",
    render: (row) => formatAmount(row.grand_total, row.currency),
  },
  { label: "Status", render: (row) => row.status || formatDocstatus(row.docstatus) },
];

const paymentColumns: DocumentColumn<any>[] = [
  { label: "Date", render: (row) => formatDate(row.posting_date) },
  { label: "Payment", render: (row) => row.name },
  { label: "Mode", render: (row) => row.mode_of_payment || "—" },
  {
    label: "Amount",
    align: "right",
    render: (row) =>
      formatAmount(
        row.received_amount || row.paid_amount,
        row.paid_to_account_currency || row.paid_from_account_currency,
      ),
  },
  { label: "Reference", render: (row) => row.reference_no || "—" },
  { label: "Status", render: (row) => row.status || formatDocstatus(row.docstatus) },
];

const meterReadingColumns: DocumentColumn<any>[] = [
  { label: "Date", render: (row) => formatDate(row.date) },
  { label: "Reading", render: (row) => row.name },
  { label: "Customer", render: (row) => row.customer },
  { label: "Status", render: (row) => formatDocstatus(row.docstatus) },
];

const serviceRequestColumns: DocumentColumn<any>[] = [
  { label: "Date", render: (row) => formatDate(row.date) },
  { label: "Request", render: (row) => row.name },
  { label: "Type", render: (row) => row.request_type || "—" },
  { label: "Status", render: (row) => row.request_status || "—" },
];

export function PropertyDocumentsView({
  documents,
}: {
  documents: PropertyDocuments;
}) {
  const tabs: TabDefinition[] = [
    {
      value: "invoices",
      label: `Invoices (${documents.sales_invoices.length})`,
      rows: documents.sales_invoices,
      columns: invoiceColumns,
      emptyMessage: "No invoices have been raised for this unit yet.",
    },
    {
      value: "orders",
      label: `Orders (${documents.sales_orders.length})`,
      rows: documents.sales_orders,
      columns: orderColumns,
      emptyMessage: "No sales orders have been raised for this unit yet.",
    },
    {
      value: "payments",
      label: `Payments (${documents.payment_entries.length})`,
      rows: documents.payment_entries,
      columns: paymentColumns,
      emptyMessage: "No payments have been recorded for this unit yet.",
    },
    {
      value: "meter-readings",
      label: `Meter Readings (${documents.meter_readings.length})`,
      rows: documents.meter_readings,
      columns: meterReadingColumns,
      emptyMessage: "No meter readings have been recorded for this unit yet.",
    },
    {
      value: "service-requests",
      label: `Service Requests (${documents.service_requests.length})`,
      rows: documents.service_requests,
      columns: serviceRequestColumns,
      emptyMessage: "No service requests were raised for this unit.",
    },
  ];

  return (
    <Tabs defaultValue="invoices" className="space-y-4">
      <TabsList className="flex-wrap">
        {tabs.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value} className="cursor-pointer">
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>

      {tabs.map((tab) => (
        <TabsContent key={tab.value} value={tab.value}>
          <DocumentTable
            rows={tab.rows}
            columns={tab.columns}
            emptyMessage={tab.emptyMessage}
          />
        </TabsContent>
      ))}
    </Tabs>
  );
}
