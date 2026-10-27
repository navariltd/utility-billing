/** Sticky summary of the unit and the selected lease terms. */

"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatAmount } from "@/lib/format";
import type { BookingOptions } from "@/types/bookings";
import { Building2, CalendarDays, MapPin } from "lucide-react";
import { longDate } from "./booking-dates";

interface BookingSummaryProps {
  options: BookingOptions;
  startDate: string;
  endDate: string;
  months: number;
}

/** Unit card, lease period and cost breakdown that follows the wizard. */
export function BookingSummary({
  options,
  startDate,
  endDate,
  months,
}: BookingSummaryProps) {
  const property = options.property;
  const location = [property.unit_number, property.location]
    .filter(Boolean)
    .join(" · ");
  const totalRent = options.monthly_rent * months;
  const dueAtMoveIn = options.monthly_rent + options.deposit_amount;

  return (
    <div className="space-y-4 lg:sticky lg:top-4">
      <Card className="overflow-hidden">
        <div className="bg-muted relative aspect-[16/9] w-full">
          {property.cover_image ? (
            <img
              src={property.cover_image}
              alt={property.property_name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="text-muted-foreground flex h-full items-center justify-center">
              <Building2 className="h-8 w-8" />
            </div>
          )}
          <span className="bg-background/90 absolute top-3 left-3 rounded-full px-2.5 py-1 text-xs font-medium backdrop-blur">
            {property.unit_type || "Rental unit"}
          </span>
        </div>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{property.property_name}</CardTitle>
          <CardDescription className="flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5" />
            {location || "Location shared on request"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="flex items-end justify-between gap-2">
            <div>
              <p className="text-2xl font-semibold">
                {formatAmount(options.monthly_rent, options.currency)}
              </p>
              <p className="text-muted-foreground text-xs">per month</p>
            </div>
            <div className="text-right">
              <p className="font-medium">
                {formatAmount(options.deposit_amount, options.currency)}
              </p>
              <p className="text-muted-foreground text-xs">deposit</p>
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <p className="text-muted-foreground flex items-center gap-2 text-xs">
              <CalendarDays className="h-3.5 w-3.5" />
              Lease period
            </p>
            <p className="font-medium">
              {longDate(startDate)} → {longDate(endDate)}
            </p>
            <p className="text-muted-foreground text-xs">
              {months} {months === 1 ? "month" : "months"}
            </p>
          </div>

          <Separator />

          <div className="space-y-1.5">
            <div className="text-muted-foreground flex justify-between text-xs">
              <span>Rent ({months} months)</span>
              <span>{formatAmount(totalRent, options.currency)}</span>
            </div>
            <div className="text-muted-foreground flex justify-between text-xs">
              <span>Deposit</span>
              <span>{formatAmount(options.deposit_amount, options.currency)}</span>
            </div>
            <div className="flex justify-between pt-1 text-sm font-semibold">
              <span>Due at move-in</span>
              <span>{formatAmount(dueAtMoveIn, options.currency)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <p className="text-muted-foreground px-1 text-xs">
        Booking requests are free. You only pay after the property manager
        confirms availability and issues the tenancy charges.
      </p>
    </div>
  );
}
