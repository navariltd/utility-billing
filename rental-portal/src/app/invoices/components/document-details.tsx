/**
 * Details of one invoice or order.
 *
 * The page composes the layout only: a hero with the amount due and its due
 * state, a KPI strip, the items / meter readings / taxes tabs and the sticky
 * summary panel with the payment action.
 *
 * The payload comes from `get_customer_document`, which scopes the document to
 * the caller's Customers server side.
 */

"use client";

import {
  DetailHero,
  documentStatusTone,
  StatTile,
  StatusPill,
} from "@/components/details";
import { BaseLayout } from "@/components/layouts/base-layout";
import { PaymentDialog } from "@/components/payments/payment-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { daysUntil, formatAmount, formatDate } from "@/lib/format";
import type { CustomerDocumentDetail } from "@/types/payments";
import { useFrappeGetCall } from "frappe-react-sdk";
import {
  ArrowLeft,
  Building2,
  CalendarClock,
  CalendarDays,
  Coins,
  Percent,
  ReceiptText,
  SearchX,
  ShoppingCart,
  Wallet,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import type { ReferenceDoctype } from "./document-labels";
import { DOCUMENT_LABELS } from "./document-labels";
import { DocumentFactsCard, SummaryCard } from "./document-side-panel";
import { ItemsCard, MeterReadingsCard, TaxesCard } from "./document-sections";

interface DocumentResponse {
  message: CustomerDocumentDetail;
}

export function DocumentDetailsView({
  referenceDoctype,
  referenceName,
}: {
  referenceDoctype: ReferenceDoctype;
  referenceName: string;
}) {
  const labels = DOCUMENT_LABELS[referenceDoctype];
  const [paying, setPaying] = useState(false);

  const { data, isLoading, error, mutate } =
    useFrappeGetCall<DocumentResponse>(
      "utility_billing.api.portal.payments.get_customer_document",
      { reference_doctype: referenceDoctype, reference_name: referenceName },
      referenceName
        ? `portal-customer-document-${referenceDoctype}-${referenceName}`
        : null,
    );

  const document_ = data?.message;

  if (referenceName && isLoading && !document_) {
    return (
      <BaseLayout>
        <div className="mx-auto w-full max-w-6xl space-y-4 px-4 lg:px-6">
          <Skeleton className="h-36 w-full rounded-2xl" />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <Skeleton className="h-72 rounded-xl lg:col-span-2" />
            <Skeleton className="h-72 rounded-xl" />
          </div>
        </div>
      </BaseLayout>
    );
  }

  if (error || !document_) {
    return (
      <BaseLayout
        title={`${labels.noun} unavailable`}
        description={`We could not load this ${labels.noun.toLowerCase()}.`}
      >
        <div className="px-4 lg:px-6">
          <Card>
            <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-16 text-center text-sm">
              <SearchX className="size-6" />
              {error?.message ||
                `Please check the ${labels.noun.toLowerCase()} number and try again.`}
              <div className="flex gap-2">
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="cursor-pointer"
                >
                  <Link to="/invoices">Back to invoices</Link>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="cursor-pointer"
                  onClick={() => mutate()}
                >
                  Retry
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </BaseLayout>
    );
  }

  const currency = document_.currency;
  const postedDate = document_.posting_date ?? document_.transaction_date;
  const dueDate = document_.due_date ?? document_.delivery_date;
  const payable = Number(document_.payable_amount ?? 0);
  const paid =
    referenceDoctype === "Sales Invoice"
      ? document_.paid_amount
      : document_.advance_paid;
  const days = daysUntil(dueDate);

  return (
    <BaseLayout>
      <div className="mx-auto w-full max-w-6xl space-y-4 px-4 lg:px-6">
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="text-muted-foreground -ml-2 cursor-pointer"
        >
          <Link to="/invoices">
            <ArrowLeft className="size-4" />
            {labels.listTitle}
          </Link>
        </Button>

        <DetailHero
          icon={referenceDoctype === "Sales Invoice" ? ReceiptText : ShoppingCart}
          eyebrow={referenceDoctype}
          title={document_.name}
          description={document_.customer_name || document_.customer}
          badges={
            <>
              <StatusPill
                label={document_.status || labels.noun}
                tone={documentStatusTone(document_.status)}
              />
              <DueState payable={payable} days={days} dueLabel={labels.dueLabel} />
            </>
          }
          meta={[
            {
              icon: CalendarDays,
              label: `${labels.dateLabel}: ${formatDate(postedDate)}`,
            },
            {
              icon: CalendarClock,
              label: `${labels.dueLabel}: ${formatDate(dueDate)}`,
            },
            ...(document_.company
              ? [{ icon: Building2, label: document_.company }]
              : []),
          ]}
          aside={
            <>
              <p className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
                {labels.amountDueLabel}
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums sm:text-3xl">
                {formatAmount(payable, currency)}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                of {formatAmount(document_.grand_total, currency)}{" "}
                {labels.noun.toLowerCase()}
              </p>
            </>
          }
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatTile
            label="Net total"
            value={formatAmount(document_.net_total, currency)}
            icon={Coins}
          />
          <StatTile
            label="Taxes"
            value={formatAmount(document_.total_taxes_and_charges, currency)}
            icon={Percent}
            tone="info"
          />
          <StatTile
            label="Grand total"
            value={formatAmount(document_.grand_total, currency)}
            icon={ReceiptText}
            tone="primary"
          />
          <StatTile
            label={labels.paidLabel}
            value={formatAmount(paid, currency)}
            icon={Wallet}
            tone="success"
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Tabs defaultValue="items" className="gap-3">
              <TabsList className="w-full justify-start overflow-x-auto sm:w-auto">
                <TabsTrigger value="items" className="cursor-pointer">
                  Items
                  <span className="text-muted-foreground tabular-nums">
                    {document_.lines.length}
                  </span>
                </TabsTrigger>
                {document_.meter_readings.length ? (
                  <TabsTrigger value="readings" className="cursor-pointer">
                    Meter readings
                    <span className="text-muted-foreground tabular-nums">
                      {document_.meter_readings.length}
                    </span>
                  </TabsTrigger>
                ) : null}
                <TabsTrigger value="taxes" className="cursor-pointer">
                  Taxes
                  <span className="text-muted-foreground tabular-nums">
                    {document_.taxes.length}
                  </span>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="items">
                <ItemsCard lines={document_.lines} />
              </TabsContent>

              {document_.meter_readings.length ? (
                <TabsContent value="readings">
                  <MeterReadingsCard readings={document_.meter_readings} />
                </TabsContent>
              ) : null}

              <TabsContent value="taxes">
                <TaxesCard taxes={document_.taxes} currency={currency} />
              </TabsContent>
            </Tabs>
          </div>

          <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
            <SummaryCard
              document={document_}
              labels={labels}
              onPay={() => setPaying(true)}
            />
            <DocumentFactsCard document={document_} labels={labels} />
          </div>
        </div>
      </div>

      {paying ? (
        <PaymentDialog
          open
          onOpenChange={(open) => {
            if (!open) {
              setPaying(false);
              mutate();
            }
          }}
          referenceDoctype={referenceDoctype}
          referenceName={document_.name}
          amount={payable}
          currency={currency}
        />
      ) : null}
    </BaseLayout>
  );
}

/** Due state of a document that still has a balance. */
function DueState({
  payable,
  days,
  dueLabel,
}: {
  payable: number;
  days: number | null;
  dueLabel: string;
}) {
  if (payable <= 0 || days === null) return null;

  if (days < 0) {
    const overdue = Math.abs(days);
    return (
      <StatusPill
        label={`Overdue by ${overdue} ${overdue === 1 ? "day" : "days"}`}
        tone="danger"
      />
    );
  }

  if (days === 0) {
    return <StatusPill label={`${dueLabel} is today`} tone="warning" />;
  }

  return (
    <StatusPill
      label={`${days === 1 ? "Due tomorrow" : `Due in ${days} days`}`}
      tone="info"
    />
  );
}

