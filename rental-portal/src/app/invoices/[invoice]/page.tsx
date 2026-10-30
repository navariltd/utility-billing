/**
 * One Sales Invoice of the customer: header fields, items, meter readings,
 * taxes and totals.
 */

"use client";

import { DocumentDetailsView } from "@/app/invoices/components/document-details";
import { useParams } from "react-router-dom";

export default function InvoiceDetailsPage() {
  const { invoice } = useParams<{ invoice: string }>();

  return (
    <DocumentDetailsView
      referenceDoctype="Sales Invoice"
      referenceName={invoice ? decodeURIComponent(invoice) : ""}
    />
  );
}
