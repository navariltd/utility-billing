/**
 * One meter reading of the customer: its meter lines, the tariff blocks the
 * consumption was billed through and the total amount.
 *
 * The payload comes from `get_customer_meter_reading`, which scopes the reading
 * to the caller's Customers server side.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatAmount, formatDate, formatNumber } from "@/lib/format";
import type {
  MeterReadingDetail,
  MeterReadingItem,
  MeterReadingRate,
} from "@/types/meter-readings";
import { useFrappeGetCall } from "frappe-react-sdk";
import { ArrowLeft, SearchX } from "lucide-react";
import { Link, useParams } from "react-router-dom";

interface MeterReadingResponse {
  message: MeterReadingDetail;
}

export default function MeterReadingDetailsPage() {
  const { reading } = useParams<{ reading: string }>();
  const readingName = reading ? decodeURIComponent(reading) : "";

  const { data, isLoading, error, mutate } =
    useFrappeGetCall<MeterReadingResponse>(
      "utility_billing.api.portal.meter_readings.get_customer_meter_reading",
      { name: readingName },
      readingName ? `portal-customer-meter-reading-${readingName}` : null,
    );

  const payload = data?.message;

  if (readingName && isLoading && !payload) {
    return (
      <BaseLayout title="Meter Reading">
        <div className="space-y-4 px-4 lg:px-6">
          <Skeleton className="h-28 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      </BaseLayout>
    );
  }

  if (error || !payload) {
    return (
      <BaseLayout
        title="Meter reading unavailable"
        description="We could not load this meter reading."
      >
        <div className="px-4 lg:px-6">
          <Card>
            <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-16 text-center text-sm">
              <SearchX className="h-6 w-6" />
              {error?.message || "Please check the reading number and try again."}
              <div className="flex gap-2">
                <Button asChild variant="outline" size="sm" className="cursor-pointer">
                  <Link to="/meter-readings">Back to meter readings</Link>
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

  return (
    <BaseLayout
      title={`Meter Reading ${payload.name}`}
      description={
        payload.property_label
          ? `${payload.property_label} · ${formatDate(payload.date)}`
          : formatDate(payload.date)
      }
    >
      <div className="space-y-4 px-4 lg:px-6">
        <Button asChild variant="ghost" size="sm" className="cursor-pointer">
          <Link to="/meter-readings">
            <ArrowLeft className="mr-1 h-4 w-4" />
            All meter readings
          </Link>
        </Button>

        <div className="grid gap-4 sm:grid-cols-3">
          <SummaryCard
            title="Total consumption"
            value={formatNumber(payload.totals.consumption)}
          />
          <SummaryCard
            title="Blocks billed"
            value={String(payload.totals.blocks)}
          />
          <SummaryCard
            title="Total amount"
            value={formatAmount(payload.totals.amount, payload.currency)}
          />
        </div>

        <ReadingDetailsCard reading={payload} />
        <MeterLinesTable
          items={payload.items}
          rates={payload.rates}
          currency={payload.currency}
        />
        <BlockDistributionTable rates={payload.rates} currency={payload.currency} />
      </div>
    </BaseLayout>
  );
}

function SummaryCard({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

function ReadingDetailsCard({ reading }: { reading: MeterReadingDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Reading details</CardTitle>
        <CardAction>
          <Badge variant={reading.docstatus === 1 ? "default" : "secondary"}>
            {reading.docstatus === 1 ? "Submitted" : "Draft"}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <DetailRow label="Reading number" value={reading.name} />
          <DetailRow label="Reading date" value={formatDate(reading.date)} />
          <DetailRow label="Unit" value={reading.property_label || reading.property} />
          <DetailRow label="Customer" value={reading.customer_name || reading.customer} />
          <DetailRow label="Company" value={reading.company} />
          <DetailRow label="Price list" value={reading.price_list} />
        </dl>
      </CardContent>
    </Card>
  );
}

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="font-medium break-words">{value || "—"}</dd>
    </div>
  );
}

function lineAmounts(rates: MeterReadingRate[]): Record<string, number> {
  const amounts: Record<string, number> = {};
  for (const rate of rates) {
    const key = rate.meter_reading_item || "unassigned";
    amounts[key] = (amounts[key] ?? 0) + Number(rate.amount ?? 0);
  }

  return amounts;
}

function MeterLinesTable({
  items,
  rates,
  currency,
}: {
  items: MeterReadingItem[];
  rates: MeterReadingRate[];
  currency: string | null;
}) {
  if (items.length === 0) {
    return null;
  }

  const amounts = lineAmounts(rates);

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardHeader className="py-4">
        <CardTitle className="text-base">Meter lines</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Meter</TableHead>
              <TableHead>Item</TableHead>
              <TableHead className="text-right">Previous</TableHead>
              <TableHead className="text-right">Current</TableHead>
              <TableHead className="text-right">Consumption</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.name}>
                <TableCell className="font-medium">{item.meter_number || "—"}</TableCell>
                <TableCell>{item.item_name || item.item_code || "—"}</TableCell>
                <TableCell className="text-right">
                  {formatNumber(item.previous_reading)}
                </TableCell>
                <TableCell className="text-right">
                  {formatNumber(item.current_reading)}
                </TableCell>
                <TableCell className="text-right">
                  {formatNumber(item.consumption)}
                  {item.uom ? (
                    <span className="text-muted-foreground ml-1 text-xs">{item.uom}</span>
                  ) : null}
                </TableCell>
                <TableCell className="text-right">
                  {formatAmount(amounts[item.name] ?? 0, currency)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function BlockDistributionTable({
  rates,
  currency,
}: {
  rates: MeterReadingRate[];
  currency: string | null;
}) {
  const total = rates.reduce((sum, rate) => sum + Number(rate.amount ?? 0), 0);

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardHeader className="py-4">
        <CardTitle className="text-base">Block distribution</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {rates.length === 0 ? (
          <p className="text-muted-foreground px-4 py-8 text-sm">
            This reading has not been billed through any tariff block yet.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Meter</TableHead>
                <TableHead>Item</TableHead>
                <TableHead>Block</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
                <TableHead className="text-right">Rate</TableHead>
                <TableHead className="text-right">Amount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rates.map((rate, index) => (
                <TableRow key={`${rate.meter_reading_item}-${rate.block}-${index}`}>
                  <TableCell className="font-medium">
                    {rate.meter_number || "—"}
                  </TableCell>
                  <TableCell>{rate.item_name || rate.item_code || "—"}</TableCell>
                  <TableCell>{rate.block || "Flat rate"}</TableCell>
                  <TableCell className="text-right">
                    {formatNumber(rate.qty)}
                    {rate.uom ? (
                      <span className="text-muted-foreground ml-1 text-xs">
                        {rate.uom}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatAmount(rate.rate, currency)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatAmount(rate.amount, currency)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colSpan={5} className="font-medium">
                  Total
                </TableCell>
                <TableCell className="text-right font-semibold">
                  {formatAmount(total, currency)}
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

