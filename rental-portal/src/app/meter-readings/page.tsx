/**
 * All meter readings recorded for the customer's units.
 *
 * Readings are tenancy independent: the page lists every non-cancelled
 * `Meter Reading` billed to the caller's Customers, newest first. Selecting a
 * row opens the reading with its meter lines, amount and tariff blocks.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { Badge } from "@/components/ui/badge";
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
import { formatAmount, formatDate, formatNumber } from "@/lib/format";
import type {
  CustomerMeterReadings,
  MeterReadingRow,
} from "@/types/meter-readings";
import { useFrappeGetCall } from "frappe-react-sdk";
import { ChevronRight, Gauge } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface MeterReadingsResponse {
  message: CustomerMeterReadings;
}


export default function MeterReadingsPage() {
  const { data, isLoading, error, mutate } =
    useFrappeGetCall<MeterReadingsResponse>(
      "utility_billing.api.portal.meter_readings.get_customer_meter_readings",
      {},
      "portal-customer-meter-readings",
    );

  const payload = data?.message;
  const readings = payload?.meter_readings ?? [];

  return (
    <BaseLayout
      title="Meter Readings"
      description={
        payload?.customer
          ? `Meter readings recorded for ${payload.customer}`
          : "Meter readings recorded for your units"
      }
    >
      <div className="space-y-4 px-4 lg:px-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard title="Readings" value={String(payload?.totals.readings ?? 0)} />
          <SummaryCard
            title="Total consumption"
            value={formatNumber(payload?.totals.consumption ?? 0)}
          />
          <SummaryCard
            title="Billed"
            value={formatAmount(payload?.totals.amount ?? 0, payload?.totals.currency)}
          />
          <SummaryCard
            title="Latest reading"
            value={formatDate(payload?.totals.latest_date)}
          />
        </div>

        {error ? (
          <Card>
            <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-12 text-sm">
              <Gauge className="h-6 w-6" />
              {error.message || "Could not load your meter readings."}
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
          <ReadingsTable loading={isLoading} readings={readings} />
        )}
      </div>
    </BaseLayout>
  );
}

function readingUrl(reading: MeterReadingRow): string {
  return `/meter-readings/${encodeURIComponent(reading.name)}`;
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

const HEADERS = [
  "Date",
  "Reading",
  "Unit",
  "Meters",
  "Consumption",
  "Amount",
  "Status",
  "",
];

function ReadingsTable({
  loading,
  readings,
}: {
  loading: boolean;
  readings: MeterReadingRow[];
}) {
  const navigate = useNavigate();

  if (loading) {
    return <Skeleton className="h-48 w-full rounded-xl" />;
  }

  if (readings.length === 0) {
    return (
      <Card>
        <CardContent className="text-muted-foreground flex flex-col items-center gap-2 py-12 text-sm">
          <Gauge className="h-6 w-6" />
          No meter readings have been recorded for your units yet.
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
              {HEADERS.map((header, index) => (
                <TableHead
                  key={header || "open"}
                  className={index >= HEADERS.length - 2 ? "text-right" : undefined}
                >
                  {header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {readings.map((reading) => (
              <TableRow
                key={reading.name}
                role="link"
                tabIndex={0}
                aria-label={`Open meter reading ${reading.name}`}
                className="cursor-pointer"
                onClick={() => navigate(readingUrl(reading))}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    navigate(readingUrl(reading));
                  }
                }}
              >
                <TableCell>{formatDate(reading.date)}</TableCell>
                <TableCell className="font-medium">{reading.name}</TableCell>
                <TableCell>{reading.property_label || "—"}</TableCell>
                <TableCell>
                  {reading.items.length ? (
                    <div className="space-y-0.5">
                      {reading.items.map((item) => (
                        <p key={item.meter_number || item.item_code}>
                          {item.meter_number || "—"}
                          <span className="text-muted-foreground ml-1 text-xs">
                            {item.item_name || item.item_code || ""}
                          </span>
                        </p>
                      ))}
                    </div>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell>
                  {formatNumber(reading.total_consumption)}
                  {reading.items.length === 1 && reading.items[0].uom ? (
                    <span className="text-muted-foreground ml-1 text-xs">
                      {reading.items[0].uom}
                    </span>
                  ) : null}
                </TableCell>
                <TableCell>
                  {formatAmount(reading.total_amount, reading.currency)}
                </TableCell>
                <TableCell className="text-right">
                  <Badge variant={reading.docstatus === 1 ? "default" : "secondary"}>
                    {reading.docstatus === 1 ? "Submitted" : "Draft"}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <ChevronRight className="text-muted-foreground ml-auto h-4 w-4" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
