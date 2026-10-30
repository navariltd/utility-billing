/**
 * One Sales Order of the customer: header fields, items, meter readings, taxes
 * and totals.
 */

"use client";

import { DocumentDetailsView } from "@/app/invoices/components/document-details";
import { useParams } from "react-router-dom";

export default function OrderDetailsPage() {
  const { order } = useParams<{ order: string }>();

  return (
    <DocumentDetailsView
      referenceDoctype="Sales Order"
      referenceName={order ? decodeURIComponent(order) : ""}
    />
  );
}
