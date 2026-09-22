/**
 * Side panel of the property details page.
 *
 * Shows the booking action for available units, or the tenancy summary (with the
 * account totals) when the property belongs to the signed in user.
 */

"use client";

import { tenancyTone, PropertyStatusBadge } from "@/components/properties";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { PropertyDetailsPayload } from "@/types/property-details";
import { CalendarDays, FileSignature } from "lucide-react";
import { Link } from "react-router-dom";

function formatDate(value?: string | null): string | null {
  if (!value) return null;

  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatAmount(
  value: number | null | undefined,
  currency?: string | null,
): string {
  const amount = Number(value ?? 0);
  if (!currency) {
    return amount.toLocaleString();
  }

  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
}

export function PropertySidePanel({
  payload,
}: {
  payload: PropertyDetailsPayload;
}) {
  const { tenancy, documents, can_book } = payload;
  const period = [
    formatDate(tenancy?.start_date),
    formatDate(tenancy?.end_date),
  ]
    .filter(Boolean)
    .join(" → ");

  return (
    <div className="space-y-4 lg:sticky lg:top-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {can_book ? "Available to rent" : tenancy ? "Your unit" : "Status"}
          </CardTitle>
          <CardDescription>
            {can_book
              ? "Reserve this unit online and we will follow up with the tenancy agreement."
              : tenancy
                ? "The details below are from your tenancy agreement."
                : "This unit is currently not open for bookings."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {can_book ? (
            <Button asChild className="w-full cursor-pointer">
              <Link to={`/properties/${encodeURIComponent(payload.property.name)}/book`}>
                Book Now
              </Link>
            </Button>
          ) : null}

          {tenancy ? (
            <>
              <div className="flex items-center gap-2 text-sm">
                <PropertyStatusBadge
                  label={tenancy.state}
                  tone={tenancyTone(tenancy.state)}
                />
                <span className="text-muted-foreground">
                  {tenancy.is_current ? "Current tenancy" : "Past tenancy"}
                </span>
              </div>
              <div className="space-y-2 text-sm">
                <span className="flex items-center gap-2">
                  <FileSignature className="h-4 w-4" />
                  {tenancy.contract}
                  <PropertyStatusBadge
                    label={
                      tenancy.contract_status ||
                      (tenancy.is_signed ? "Signed" : "Unsigned")
                    }
                    tone="neutral"
                  />
                </span>
                {period ? (
                  <span className="text-muted-foreground flex items-center gap-2">
                    <CalendarDays className="h-4 w-4" />
                    {period}
                  </span>
                ) : null}
              </div>
            </>
          ) : null}

          {!can_book && !tenancy ? (
            <Button asChild variant="outline" className="w-full cursor-pointer">
              <Link to="/properties">Browse available properties</Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>

      {documents ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account summary</CardTitle>
            <CardDescription>Totals for this unit</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Invoiced</span>
              <span className="font-medium">
                {formatAmount(documents.totals.invoiced, documents.totals.currency)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Paid</span>
              <span className="font-medium">
                {formatAmount(documents.totals.paid, documents.totals.currency)}
              </span>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Outstanding</span>
              <span className="font-semibold">
                {formatAmount(documents.totals.outstanding, documents.totals.currency)}
              </span>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
