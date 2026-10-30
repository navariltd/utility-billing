/**
 * All submitted invoices and sales orders of the customer.
 *
 * This page is independent of a tenancy: it lists every payable document and
 * only offers the payment action. Outstanding invoices are paid directly;
 * sales orders are paid as an advance.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { PaymentDialog } from "@/components/payments/payment-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatAmount, formatDate } from "@/lib/format";
import type { CustomerDocuments } from "@/types/payments";
import { useFrappeGetCall } from "frappe-react-sdk";
import { CreditCard, FileText } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

interface DocumentsResponse {
  message: CustomerDocuments;
}

interface PaymentTarget {
  doctype: "Sales Invoice" | "Sales Order";
  name: string;
  amount: number;
  currency: string | null;
}

export default function InvoicesPage() {
  const { data, isLoading, error, mutate } = useFrappeGetCall<DocumentsResponse>(
    "utility_billing.api.portal.payments.get_customer_documents",
    {},
    "portal-customer-documents",
  );
  const [payment, setPayment] = useState<PaymentTarget | null>(null);

  const documents = data?.message;
  const invoices = documents?.invoices ?? [];
  const orders = documents?.orders ?? [];
  const outstanding = Object.entries(documents?.totals.outstanding ?? {});
  const advances = Object.entries(documents?.totals.advances ?? {});

  return (
    <BaseLayout
      title="Invoices & Orders"
      description="Every submitted billing document on your account"
    >
      <div className="space-y-4 px-4 lg:px-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <SummaryCard title="Outstanding invoices" totals={outstanding} />
          <SummaryCard title="Order balances" totals={advances} />
        </div>

        {error ? (
          <Card>
            <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-12 text-sm">
              <FileText className="h-6 w-6" />
              {error.message || "Could not load your documents."}
              <Button
                variant="outline"
                size="sm"
                className="cursor-pointer"
                onClick={() => mutate()}
              >
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="invoices" className="space-y-4">
            <TabsList>
              <TabsTrigger value="invoices" className="cursor-pointer">
                Invoices ({invoices.length})
              </TabsTrigger>
              <TabsTrigger value="orders" className="cursor-pointer">
                Orders ({orders.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="invoices">
              <DocumentsTable
                loading={isLoading}
                emptyMessage="No outstanding invoices."
                headers={["Invoice", "Date", "Due", "Outstanding", "Status", ""]}
                rows={invoices.map((invoice) => ({
                  key: invoice.name,
                  href: `/invoices/${encodeURIComponent(invoice.name)}`,
                  cells: [
                    <Link
                      key="name"
                      to={`/invoices/${encodeURIComponent(invoice.name)}`}
                      className="font-medium underline-offset-4 hover:underline"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {invoice.name}
                    </Link>,
                    formatDate(invoice.posting_date),
                    formatDate(invoice.due_date),
                    formatAmount(invoice.payable_amount, invoice.currency),
                    invoice.status || "—",
                    <Button
                      key="pay"
                      size="sm"
                      className="cursor-pointer"
                      onClick={(event) => {
                        event.stopPropagation();
                        setPayment({
                          doctype: "Sales Invoice",
                          name: invoice.name,
                          amount: invoice.payable_amount,
                          currency: invoice.currency,
                        });
                      }}
                    >
                      <CreditCard className="mr-2 h-4 w-4" />
                      Pay
                    </Button>,
                  ],
                }))}
              />
            </TabsContent>

            <TabsContent value="orders">
              <DocumentsTable
                loading={isLoading}
                emptyMessage="No sales orders with a balance."
                headers={["Order", "Date", "Delivery", "Balance", "Status", ""]}
                rows={orders.map((order) => ({
                  key: order.name,
                  href: `/orders/${encodeURIComponent(order.name)}`,
                  cells: [
                    <Link
                      key="name"
                      to={`/orders/${encodeURIComponent(order.name)}`}
                      className="font-medium underline-offset-4 hover:underline"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {order.name}
                    </Link>,
                    formatDate(order.transaction_date),
                    formatDate(order.delivery_date),
                    formatAmount(order.payable_amount, order.currency),
                    order.status || "—",
                    <Button
                      key="pay"
                      size="sm"
                      className="cursor-pointer"
                      onClick={(event) => {
                        event.stopPropagation();
                        setPayment({
                          doctype: "Sales Order",
                          name: order.name,
                          amount: order.payable_amount,
                          currency: order.currency,
                        });
                      }}
                    >
                      <CreditCard className="mr-2 h-4 w-4" />
                      Pay advance
                    </Button>,
                  ],
                }))}
              />
            </TabsContent>
          </Tabs>
        )}
      </div>

      {payment ? (
        <PaymentDialog
          open={Boolean(payment)}
          onOpenChange={(open) => {
            if (!open) {
              setPayment(null);
              mutate();
            }
          }}
          referenceDoctype={payment.doctype}
          referenceName={payment.name}
          amount={payment.amount}
          currency={payment.currency}
        />
      ) : null}
    </BaseLayout>
  );
}

function SummaryCard({
  title,
  totals,
}: {
  title: string;
  totals: [string, number][];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {totals.length === 0 ? (
          <p className="text-muted-foreground text-sm">Nothing due.</p>
        ) : (
          <div className="space-y-1">
            {totals.map(([currency, amount]) => (
              <p key={currency} className="text-2xl font-bold">
                {formatAmount(amount, currency || null)}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface TableRow {
  key: string;
  cells: ReactNode[];
  /** Path opened when the row is activated; rows stay inert when omitted. */
  href?: string;
}

function DocumentsTable({
  loading,
  emptyMessage,
  headers,
  rows,
}: {
  loading: boolean;
  emptyMessage: string;
  headers: string[];
  rows: TableRow[];
}) {
  const navigate = useNavigate();

  if (loading) {
    return <Skeleton className="h-48 w-full rounded-xl" />;
  }

  if (rows.length === 0) {
    return (
      <Card>
        <CardContent className="text-muted-foreground flex flex-col items-center gap-2 py-12 text-sm">
          <FileText className="h-6 w-6" />
          {emptyMessage}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              {headers.map((header, index) => (
                <TableHead
                  key={`${header}-${index}`}
                  className={index === headers.length - 1 ? "text-right" : undefined}
                >
                  {header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const href = row.href;

              return (
                <TableRow
                  key={row.key}
                  role={href ? "link" : undefined}
                  tabIndex={href ? 0 : undefined}
                  aria-label={href ? `Open ${row.key}` : undefined}
                  className={href ? "cursor-pointer" : undefined}
                  onClick={href ? () => navigate(href) : undefined}
                  onKeyDown={
                    href
                      ? (event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            navigate(href);
                          }
                        }
                      : undefined
                  }
                >
                  {row.cells.map((cell, index) => (
                    <TableCell
                      key={`${row.key}-${index}`}
                      className={
                        index === row.cells.length - 1 ? "text-right" : undefined
                      }
                    >
                      {cell}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
