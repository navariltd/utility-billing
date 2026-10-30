/**
 * Labels of the invoice / order detail page.
 *
 * The two documents share a layout but not a vocabulary: an invoice is posted
 * and due, an order is placed and delivered, and it is paid as an advance.
 */

export type ReferenceDoctype = "Sales Invoice" | "Sales Order";

export interface DocumentLabels {
  /** Noun used in sentences ("this invoice"). */
  noun: string;
  /** Label of the back link to the list. */
  listTitle: string;
  /** Label of the posting / order date. */
  dateLabel: string;
  /** Label of the due / delivery date. */
  dueLabel: string;
  /** Label of the amount already paid. */
  paidLabel: string;
  /** Label of the amount still open. */
  amountDueLabel: string;
}

export const DOCUMENT_LABELS: Record<ReferenceDoctype, DocumentLabels> = {
  "Sales Invoice": {
    noun: "Invoice",
    listTitle: "All invoices and orders",
    dateLabel: "Posting date",
    dueLabel: "Due date",
    paidLabel: "Paid",
    amountDueLabel: "Amount due",
  },
  "Sales Order": {
    noun: "Order",
    listTitle: "All invoices and orders",
    dateLabel: "Order date",
    dueLabel: "Delivery date",
    paidLabel: "Advance paid",
    amountDueLabel: "Balance",
  },
};
