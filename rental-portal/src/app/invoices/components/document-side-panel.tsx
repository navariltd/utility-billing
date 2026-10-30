/**
 * Side panel of an invoice or order: the amount breakdown (with the payment
 * action) and the facts of the document.
 *
 * The panel is sticky on wide screens, so the amount due and its action stay in
 * view while the items are scrolled.
 */

"use client";

import { CreditCard, ReceiptText, Scale } from "lucide-react";

import { InfoList } from "@/components/details/info-list";
import { SectionCard } from "@/components/details/section-card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { formatAmount, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CustomerDocumentDetail } from "@/types/payments";

import type { DocumentLabels } from "./document-labels";

export function SummaryCard({
  document: document_,
  labels,
  onPay,
}: {
  document: CustomerDocumentDetail;
  labels: DocumentLabels;
  onPay: () => void;
}) {
  const currency = document_.currency;
  const paid =
    labels.paidLabel === "Advance paid"
      ? document_.advance_paid
      : document_.paid_amount;
  const payable = Number(document_.payable_amount ?? 0);
  const rounded = Number(document_.rounded_total ?? 0);
  const grandTotal = Number(document_.grand_total ?? 0);

  return (
    <SectionCard title="Summary" icon={ReceiptText}>
      <div className="space-y-2.5 p-4 text-sm sm:p-5">
        <SummaryRow
          label="Net total"
          value={formatAmount(document_.net_total, currency)}
        />
        <SummaryRow
          label="Taxes"
          value={formatAmount(document_.total_taxes_and_charges, currency)}
        />
        <Separator />
        <SummaryRow
          label="Grand total"
          value={formatAmount(grandTotal, currency)}
          strong
        />
        {rounded > 0 && rounded !== grandTotal ? (
          <SummaryRow
            label="Rounded total"
            value={formatAmount(rounded, currency)}
          />
        ) : null}
        <SummaryRow
          label={labels.paidLabel}
          value={
            Number(paid ?? 0) > 0
              ? `− ${formatAmount(paid, currency)}`
              : formatAmount(0, currency)
          }
        />

        <div className="bg-primary/5 border-primary/15 mt-1 flex items-center justify-between rounded-lg border px-3 py-2.5">
          <span className="text-muted-foreground text-xs font-medium tracking-[0.1em] uppercase">
            {labels.amountDueLabel}
          </span>
          <span className="text-lg font-semibold tabular-nums">
            {formatAmount(payable, currency)}
          </span>
        </div>

        {payable > 0 ? (
          <Button className="w-full cursor-pointer" onClick={onPay}>
            <CreditCard className="size-4" />
            Pay {formatAmount(payable, currency)}
          </Button>
        ) : (
          <Button variant="outline" className="w-full" disabled>
            Fully settled
          </Button>
        )}
      </div>
    </SectionCard>
  );
}

function SummaryRow({
  label,
  value,
  strong,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("tabular-nums", strong ? "font-semibold" : "font-medium")}>
        {value}
      </span>
    </div>
  );
}

export function DocumentFactsCard({
  document: document_,
  labels,
}: {
  document: CustomerDocumentDetail;
  labels: DocumentLabels;
}) {
  return (
    <SectionCard title="Details" icon={Scale}>
      <div className="p-4 sm:p-5">
        <InfoList
          items={[
            { label: "Document", value: document_.name },
            {
              label: "Customer",
              value: document_.customer_name || document_.customer,
            },
            { label: "Company", value: document_.company },
            {
              label: labels.dateLabel,
              value: formatDate(
                document_.posting_date ?? document_.transaction_date,
              ),
            },
            {
              label: labels.dueLabel,
              value: formatDate(document_.due_date ?? document_.delivery_date),
            },
            { label: "Currency", value: document_.currency },
          ]}
        />
      </div>
    </SectionCard>
  );
}
