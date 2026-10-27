/** Final booking step: a full review of the request before it is sent. */

"use client";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { formatAmount } from "@/lib/format";
import type { BookingOptions } from "@/types/bookings";
import {
  CalendarRange,
  CircleDollarSign,
  Info,
  MapPin,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import type { ReactNode } from "react";
import { daysBetween, longDate } from "./booking-dates";

interface BookingReviewStepProps {
  options: BookingOptions;
  startDate: string;
  endDate: string;
  months: number;
  fullName: string;
  email: string;
  nrc: string;
  notes: string;
}

interface ReviewRowProps {
  label: string;
  value: string;
}

function ReviewRow({ label, value }: ReviewRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="max-w-[60%] text-right font-medium">{value}</span>
    </div>
  );
}

function ReviewSection({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof MapPin;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3 rounded-xl border p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <Icon className="text-muted-foreground h-4 w-4" />
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

/** Read-only summary of the unit, lease terms, tenant and costs. */
export function BookingReviewStep({
  options,
  startDate,
  endDate,
  months,
  fullName,
  email,
  nrc,
  notes,
}: BookingReviewStepProps) {
  const nights = startDate && endDate ? daysBetween(startDate, endDate) : 0;
  const totalRent = options.monthly_rent * months;
  const dueAtMoveIn = options.monthly_rent + options.deposit_amount;
  const location = [options.property.unit_number, options.property.location]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="space-y-4">
      <ReviewSection icon={MapPin} title="Unit">
        <ReviewRow label="Property" value={options.property.property_name} />
        {location ? <ReviewRow label="Location" value={location} /> : null}
        <ReviewRow
          label="Monthly rent"
          value={formatAmount(options.monthly_rent, options.currency)}
        />
      </ReviewSection>

      <ReviewSection icon={CalendarRange} title="Lease terms">
        <ReviewRow label="Move-in" value={longDate(startDate)} />
        <ReviewRow label="Lease end" value={longDate(endDate)} />
        <ReviewRow
          label="Duration"
          value={`${months} ${months === 1 ? "month" : "months"} · ${nights} days`}
        />
      </ReviewSection>

      <ReviewSection icon={CircleDollarSign} title="Costs">
        <ReviewRow
          label={`Rent for ${months} ${months === 1 ? "month" : "months"}`}
          value={formatAmount(totalRent, options.currency)}
        />
        <ReviewRow
          label={`Deposit (${options.deposit_months} ${
            options.deposit_months === 1 ? "month" : "months"
          })`}
          value={formatAmount(options.deposit_amount, options.currency)}
        />
        <Separator />
        <div className="flex items-center justify-between gap-4">
          <span className="text-sm font-medium">Due at move-in</span>
          <div className="text-right">
            <p className="text-lg font-semibold">
              {formatAmount(dueAtMoveIn, options.currency)}
            </p>
            <p className="text-muted-foreground text-xs">
              First month rent + deposit
            </p>
          </div>
        </div>
      </ReviewSection>

      <ReviewSection icon={UserRound} title="Tenant">
        <ReviewRow label="Name" value={fullName || "—"} />
        <ReviewRow label="Email" value={email || "—"} />
        <ReviewRow label="Customer" value={options.customer.customer_name} />
        {nrc ? <ReviewRow label="NRC / Passport" value={nrc} /> : null}
      </ReviewSection>

      {notes ? (
        <ReviewSection icon={Info} title="Notes">
          <p className="text-muted-foreground text-sm whitespace-pre-line">
            {notes}
          </p>
        </ReviewSection>
      ) : null}

      <div className="border-primary/20 bg-primary/5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed p-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-primary h-5 w-5" />
          <div>
            <p className="text-sm font-medium">No payment taken now</p>
            <p className="text-muted-foreground text-xs">
              Payment instructions follow once the manager approves the booking.
            </p>
          </div>
        </div>
        <Badge variant="secondary">Review pending</Badge>
      </div>
    </div>
  );
}
