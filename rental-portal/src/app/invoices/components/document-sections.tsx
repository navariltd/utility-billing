/**
 * Sections of an invoice or order: the items, the meter readings the document
 * was built from and the taxes.
 *
 * The header facts and the amount summary live in `document-side-panel.tsx`;
 * `document-details.tsx` only composes the layout and the page state.
 */

"use client";

import {
  ArrowRight,
  ArrowUpRight,
  Gauge,
  ListTree,
  Receipt,
} from "lucide-react";
import { Link } from "react-router-dom";

import { CountPill, SectionCard } from "@/components/details/section-card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatAmount, formatNumber } from "@/lib/format";
import type {
  DocumentLine,
  DocumentMeterReading,
  DocumentTax,
} from "@/types/payments";

export function ItemsCard({ lines }: { lines: DocumentLine[] }) {
  const total = lines.reduce((sum, line) => sum + Number(line.amount ?? 0), 0);

  return (
    <SectionCard
      title="Items"
      icon={ListTree}
      action={<CountPill>{lines.length}</CountPill>}
    >
      {lines.length === 0 ? (
        <p className="text-muted-foreground px-4 py-10 text-center text-sm">
          This document has no items.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4 sm:pl-5">Item</TableHead>
              <TableHead className="text-right">Quantity</TableHead>
              <TableHead className="text-right">Rate</TableHead>
              <TableHead className="pr-4 text-right sm:pr-5">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {lines.map((line, index) => (
              <TableRow key={`${line.item_code}-${index}`}>
                <TableCell className="pl-4 sm:pl-5">
                  <p className="font-medium">{line.item_name || line.item_code}</p>
                  {line.description &&
                  line.description !== (line.item_name || line.item_code) ? (
                    <p className="text-muted-foreground mt-0.5 max-w-prose text-xs">
                      {line.description}
                    </p>
                  ) : null}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap tabular-nums">
                  {formatNumber(line.qty)}
                  {line.uom ? (
                    <span className="text-muted-foreground ml-1 text-xs">
                      {line.uom}
                    </span>
                  ) : null}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap tabular-nums">
                  {formatAmount(line.rate)}
                </TableCell>
                <TableCell className="pr-4 text-right font-medium whitespace-nowrap tabular-nums sm:pr-5">
                  {formatAmount(line.amount)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={3} className="pl-4 font-medium sm:pl-5">
                Total
              </TableCell>
              <TableCell className="pr-4 text-right font-semibold tabular-nums sm:pr-5">
                {formatAmount(total)}
              </TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )}
    </SectionCard>
  );
}

export function MeterReadingsCard({
  readings,
}: {
  readings: DocumentMeterReading[];
}) {
  return (
    <SectionCard
      title="Meter readings"
      description="The readings this document was billed from."
      icon={Gauge}
      action={<CountPill>{readings.length}</CountPill>}
    >
      <div className="grid gap-3 p-4 sm:grid-cols-2 sm:p-5">
        {readings.map((reading, index) => {
          const consumption = Number(reading.consumption ?? 0);
          const current = Number(reading.current_reading ?? 0);
          const share =
            current > 0 ? Math.min(100, (consumption / current) * 100) : 0;

          return (
            <div
              key={`${reading.meter_number}-${index}`}
              className="bg-muted/30 space-y-3 rounded-lg border p-3.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm font-semibold">
                    {reading.meter_number || "—"}
                  </p>
                  <p className="text-muted-foreground truncate text-xs">
                    {reading.item_code || "Meter"}
                  </p>
                </div>
                <span className="bg-background rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap tabular-nums">
                  {formatNumber(consumption)}
                  {reading.uom ? (
                    <span className="text-muted-foreground"> {reading.uom}</span>
                  ) : null}
                </span>
              </div>

              <div className="text-muted-foreground flex items-center gap-2 text-xs tabular-nums">
                <span>{formatNumber(reading.previous_reading)}</span>
                <ArrowRight className="size-3" />
                <span className="text-foreground font-medium">
                  {formatNumber(reading.current_reading)}
                </span>
              </div>

              <Progress value={share} className="h-1.5" />

              {reading.meter_reading ? (
                <Link
                  to={`/meter-readings/${encodeURIComponent(reading.meter_reading)}`}
                  className="text-primary inline-flex items-center gap-1 text-xs font-medium underline-offset-4 hover:underline"
                >
                  View reading
                  <ArrowUpRight className="size-3" />
                </Link>
              ) : null}
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}

const CHARGE_TYPE_LABELS: Record<string, string> = {
  Actual: "Actual",
  "On Net Total": "On net total",
  "On Previous Row Amount": "On previous amount",
  "On Previous Row Total": "On previous total",
  "On Item Quantity": "On quantity",
};

export function TaxesCard({
  taxes,
  currency,
}: {
  taxes: DocumentTax[];
  currency: string | null;
}) {
  const total = taxes.reduce((sum, tax) => sum + Number(tax.tax_amount ?? 0), 0);

  return (
    <SectionCard
      title="Taxes & charges"
      icon={Receipt}
      action={<CountPill>{taxes.length}</CountPill>}
    >
      {taxes.length === 0 ? (
        <p className="text-muted-foreground px-4 py-10 text-center text-sm">
          No taxes were applied to this document.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4 sm:pl-5">Description</TableHead>
              <TableHead className="hidden sm:table-cell">Basis</TableHead>
              <TableHead className="text-right">Rate</TableHead>
              <TableHead className="pr-4 text-right sm:pr-5">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {taxes.map((tax, index) => (
              <TableRow key={`${tax.description}-${index}`}>
                <TableCell className="pl-4 font-medium sm:pl-5">
                  {tax.description || "—"}
                </TableCell>
                <TableCell className="text-muted-foreground hidden text-xs sm:table-cell">
                  {CHARGE_TYPE_LABELS[tax.charge_type ?? ""] ||
                    tax.charge_type ||
                    "—"}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap tabular-nums">
                  {tax.charge_type === "Actual"
                    ? formatAmount(tax.tax_amount, currency)
                    : `${formatNumber(tax.rate)}%`}
                </TableCell>
                <TableCell className="pr-4 text-right font-medium whitespace-nowrap tabular-nums sm:pr-5">
                  {formatAmount(tax.tax_amount, currency)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={3} className="pl-4 font-medium sm:pl-5">
                Total taxes
              </TableCell>
              <TableCell className="pr-4 text-right font-semibold tabular-nums sm:pr-5">
                {formatAmount(total, currency)}
              </TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )}
    </SectionCard>
  );
}
