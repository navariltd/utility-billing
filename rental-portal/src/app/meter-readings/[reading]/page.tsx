/**
 * One meter reading of the customer: the consumption, the meters that were read
 * and the tariff blocks the consumption was billed through.
 *
 * The payload comes from `get_customer_meter_reading`, which scopes the reading
 * to the caller's Customers server side.
 */

"use client";

import {
  CountPill,
  DetailHero,
  InfoList,
  SectionCard,
  readingStatus,
  StatTile,
  StatusPill,
} from "@/components/details";
import { BaseLayout } from "@/components/layouts/base-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatAmount, formatDate, formatNumber } from "@/lib/format";
import type {
  MeterReadingDetail,
  MeterReadingItem,
  MeterReadingRate,
} from "@/types/meter-readings";
import { useFrappeGetCall } from "frappe-react-sdk";
import {
  ArrowLeft,
  Building2,
  CalendarDays,
  Coins,
  Gauge,
  Layers,
  ReceiptText,
  Scale,
  SearchX,
  Timer,
} from "lucide-react";
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

  if (error || !payload) {
    return (
      <BaseLayout
        title="Meter reading unavailable"
        description="We could not load this meter reading."
      >
        <div className="px-4 lg:px-6">
          <Card>
            <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-16 text-center text-sm">
              <SearchX className="size-6" />
              {error?.message || "Please check the reading number and try again."}
              <div className="flex gap-2">
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="cursor-pointer"
                >
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

  const status = readingStatus(payload.docstatus);
  const currency = payload.currency;
  const unit = payload.property_label || payload.property;
  const amounts = lineAmounts(payload.rates);

  return (
    <BaseLayout>
      <div className="mx-auto w-full max-w-6xl space-y-4 px-4 lg:px-6">
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="text-muted-foreground -ml-2 cursor-pointer"
        >
          <Link to="/meter-readings">
            <ArrowLeft className="size-4" />
            All meter readings
          </Link>
        </Button>

        <DetailHero
          icon={Gauge}
          eyebrow="Meter reading"
          title={payload.name}
          description={
            [unit, payload.customer_name || payload.customer]
              .filter(Boolean)
              .join(" · ")
          }
          badges={<StatusPill label={status.label} tone={status.tone} />}
          meta={[
            { icon: CalendarDays, label: formatDate(payload.date) },
            ...(payload.company
              ? [{ icon: Building2, label: payload.company }]
              : []),
            ...(payload.price_list
              ? [{ icon: Scale, label: payload.price_list }]
              : []),
          ]}
          aside={
            <>
              <p className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
                Total amount
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums sm:text-3xl">
                {formatAmount(payload.totals.amount, currency)}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                {formatNumber(payload.totals.consumption)} units consumed
              </p>
            </>
          }
        />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatTile
            label="Consumption"
            value={formatNumber(payload.totals.consumption)}
            hint={`Read on ${formatDate(payload.date)}`}
            icon={Gauge}
            tone="info"
          />
          <StatTile
            label="Meters read"
            value={formatNumber(payload.items.length)}
            hint={payload.items
              .map((item) => item.meter_number)
              .filter(Boolean)
              .join(", ")}
            icon={Timer}
          />
          <StatTile
            label="Blocks billed"
            value={formatNumber(payload.totals.blocks)}
            hint="Tariff blocks applied"
            icon={Layers}
          />
          <StatTile
            label="Amount"
            value={formatAmount(payload.totals.amount, currency)}
            hint="Charged for this reading"
            icon={Coins}
            tone="primary"
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Tabs defaultValue="meters" className="gap-3">
              <TabsList className="w-full justify-start overflow-x-auto sm:w-auto">
                <TabsTrigger value="meters" className="cursor-pointer">
                  Meter lines
                  <span className="text-muted-foreground tabular-nums">
                    {payload.items.length}
                  </span>
                </TabsTrigger>
                <TabsTrigger value="blocks" className="cursor-pointer">
                  Tariff blocks
                  <span className="text-muted-foreground tabular-nums">
                    {payload.rates.length}
                  </span>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="meters">
                <MeterLinesCard
                  items={payload.items}
                  amounts={amounts}
                  currency={currency}
                />
              </TabsContent>

              <TabsContent value="blocks">
                <TariffBlocksCard rates={payload.rates} currency={currency} />
              </TabsContent>
            </Tabs>
          </div>

          <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
            <SectionCard title="Summary" icon={ReceiptText}>
              <div className="space-y-3 p-4 sm:p-5">
                <InfoList
                  items={[
                    {
                      label: "Consumption",
                      value: formatNumber(payload.totals.consumption),
                    },
                    {
                      label: "Blocks billed",
                      value: formatNumber(payload.totals.blocks),
                    },
                    {
                      label: "Price list",
                      value: payload.price_list || "—",
                    },
                  ]}
                />
                <div className="bg-primary/5 border-primary/15 flex items-center justify-between rounded-lg border px-3 py-2.5">
                  <span className="text-muted-foreground text-xs font-medium tracking-[0.1em] uppercase">
                    Total amount
                  </span>
                  <span className="text-lg font-semibold tabular-nums">
                    {formatAmount(payload.totals.amount, currency)}
                  </span>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Reading details" icon={CalendarDays}>
              <div className="p-4 sm:p-5">
                <InfoList
                  items={[
                    { label: "Reading", value: payload.name },
                    { label: "Date", value: formatDate(payload.date) },
                    { label: "Unit", value: unit || "—" },
                    {
                      label: "Customer",
                      value: payload.customer_name || payload.customer,
                    },
                    { label: "Company", value: payload.company || "—" },
                    { label: "Status", value: status.label },
                  ]}
                />
              </div>
            </SectionCard>
          </div>
        </div>
      </div>
    </BaseLayout>
  );
}



/** Amount billed per meter line, summed from the tariff blocks of that line. */
function lineAmounts(rates: MeterReadingRate[]): Record<string, number> {
  return rates.reduce<Record<string, number>>((amounts, rate) => {
    if (!rate.meter_reading_item) return amounts;

    amounts[rate.meter_reading_item] =
      (amounts[rate.meter_reading_item] ?? 0) + Number(rate.amount ?? 0);

    return amounts;
  }, {});
}

function MeterLinesCard({
  items,
  amounts,
  currency,
}: {
  items: MeterReadingItem[];
  amounts: Record<string, number>;
  currency: string | null;
}) {
  const total = items.reduce((sum, item) => sum + (amounts[item.name] ?? 0), 0);
  const maxConsumption = items.reduce(
    (max, item) => Math.max(max, Number(item.consumption ?? 0)),
    0,
  );

  return (
    <SectionCard
      title="Meter lines"
      description="Previous and current readings of every meter."
      icon={Gauge}
      action={<CountPill>{items.length}</CountPill>}
    >
      {items.length === 0 ? (
        <p className="text-muted-foreground px-4 py-10 text-center text-sm">
          This reading has no meter lines.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4 sm:pl-5">Meter</TableHead>
              <TableHead className="text-right">Previous</TableHead>
              <TableHead className="text-right">Current</TableHead>
              <TableHead className="text-right">Consumption</TableHead>
              <TableHead className="pr-4 text-right sm:pr-5">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => {
              const consumption = Number(item.consumption ?? 0);
              const share =
                maxConsumption > 0
                  ? Math.min(100, (consumption / maxConsumption) * 100)
                  : 0;

              return (
                <TableRow key={item.name}>
                  <TableCell className="pl-4 sm:pl-5">
                    <p className="font-mono text-sm font-semibold">
                      {item.meter_number || "—"}
                    </p>
                    <p className="text-muted-foreground truncate text-xs">
                      {item.item_name || item.item_code || "—"}
                    </p>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-right whitespace-nowrap tabular-nums">
                    {formatNumber(item.previous_reading)}
                  </TableCell>
                  <TableCell className="text-right font-medium whitespace-nowrap tabular-nums">
                    {formatNumber(item.current_reading)}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <span className="font-medium tabular-nums">
                      {formatNumber(consumption)}
                    </span>
                    {item.uom ? (
                      <span className="text-muted-foreground ml-1 text-xs">
                        {item.uom}
                      </span>
                    ) : null}
                    <Progress value={share} className="mt-1.5 ml-auto h-1 w-20" />
                  </TableCell>
                  <TableCell className="pr-4 text-right font-medium whitespace-nowrap tabular-nums sm:pr-5">
                    {formatAmount(amounts[item.name] ?? 0, currency)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
          <TableFooter>
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={4} className="pl-4 font-medium sm:pl-5">
                Total
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

function TariffBlocksCard({
  rates,
  currency,
}: {
  rates: MeterReadingRate[];
  currency: string | null;
}) {
  const total = rates.reduce((sum, rate) => sum + Number(rate.amount ?? 0), 0);

  return (
    <SectionCard
      title="Tariff blocks"
      description="How the consumption was split across the tariff blocks."
      icon={Layers}
      action={<CountPill>{rates.length}</CountPill>}
    >
      {rates.length === 0 ? (
        <p className="text-muted-foreground px-4 py-10 text-center text-sm">
          This reading has not been billed through any tariff block yet.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4 sm:pl-5">Meter</TableHead>
              <TableHead>Block</TableHead>
              <TableHead className="text-right">Quantity</TableHead>
              <TableHead className="text-right">Rate</TableHead>
              <TableHead className="pr-4 text-right sm:pr-5">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rates.map((rate, index) => {
              const share =
                total > 0 ? (Number(rate.amount ?? 0) / total) * 100 : 0;

              return (
                <TableRow
                  key={`${rate.meter_reading_item}-${rate.block}-${index}`}
                >
                  <TableCell className="pl-4 sm:pl-5">
                    <p className="font-mono text-sm font-medium">
                      {rate.meter_number || "—"}
                    </p>
                    <p className="text-muted-foreground truncate text-xs">
                      {rate.item_name || rate.item_code || "—"}
                    </p>
                  </TableCell>
                  <TableCell className="min-w-32">
                    <p className="font-medium">{rate.block || "Flat rate"}</p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <Progress value={share} className="h-1 w-16" />
                      <span className="text-muted-foreground text-xs tabular-nums">
                        {share.toFixed(0)}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap tabular-nums">
                    {formatNumber(rate.qty)}
                    {rate.uom ? (
                      <span className="text-muted-foreground ml-1 text-xs">
                        {rate.uom}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap tabular-nums">
                    {formatAmount(rate.rate, currency)}
                  </TableCell>
                  <TableCell className="pr-4 text-right font-medium whitespace-nowrap tabular-nums sm:pr-5">
                    {formatAmount(rate.amount, currency)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
          <TableFooter>
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={4} className="pl-4 font-medium sm:pl-5">
                Total
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

