/**
 * Three step unit booking wizard: dates, tenant details, review.
 *
 * Submitting calls `utility_billing.api.portal.bookings.create_booking`, which
 * creates a draft Utility Service Request for the property manager to review,
 * then sends the tenant to My Bookings to track it.
 */

"use client";

import { parseFrappeError } from "@/components/doctype/form/parse-error";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useUser } from "@/contexts/user-context";
import { formatAmount, formatDate } from "@/lib/format";
import type { Booking, BookingOptions } from "@/types/bookings";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const CONTRACT_LENGTHS = [3, 6, 12, 24, 36];
const STEPS = ["Dates", "Tenant", "Review"];

interface BookingWizardProps {
  property: string;
}

interface OptionsResponse {
  message: BookingOptions;
}

function addMonths(value: string, months: number): string {
  const date = new Date(`${value}T00:00:00`);
  date.setMonth(date.getMonth() + months);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function BookingWizard({ property }: BookingWizardProps) {
  const { user } = useUser();
  const navigate = useNavigate();
  const { data, isLoading, error, mutate } = useFrappeGetCall<OptionsResponse>(
    "utility_billing.api.portal.bookings.get_booking_options",
    { property },
    `booking-options-${property}`,
  );
  const { call: createBooking, loading: submitting, error: submitError } =
    useFrappePostCall<Booking>(
      "utility_billing.api.portal.bookings.create_booking",
    );

  const options = data?.message;
  const [step, setStep] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [months, setMonths] = useState(12);
  const [endDate, setEndDate] = useState("");
  const [nrc, setNrc] = useState("");
  const [notes, setNotes] = useState("");
  const [validation, setValidation] = useState<string | null>(null);

  const effectiveStart = startDate || options?.default_start_date || "";
  const effectiveMonths =
    startDate && months ? months : options?.default_contract_length_months ?? 12;
  const computedEnd = useMemo(
    () =>
      endDate || (effectiveStart ? addMonths(effectiveStart, effectiveMonths) : ""),
    [endDate, effectiveStart, effectiveMonths],
  );

  const rent = options?.monthly_rent ?? 0;
  const deposit = options?.deposit_amount ?? 0;
  const estimatedTotal = rent * effectiveMonths;

  const goNext = () => {
    setValidation(null);
    if (step === 0 && (!effectiveStart || !computedEnd)) {
      setValidation("Choose the lease start and end dates.");
      return;
    }
    if (step === 0 && computedEnd <= effectiveStart) {
      setValidation("The end date must be after the start date.");
      return;
    }
    setStep((current) => Math.min(current + 1, STEPS.length - 1));
  };

  const confirm = async () => {
    setValidation(null);
    try {
      await createBooking({
        property,
        start_date: effectiveStart,
        end_date: computedEnd,
        contract_length_months: effectiveMonths,
        nrcpassport_no: nrc || undefined,
        notes: notes || undefined,
      });
      navigate("/bookings", { replace: true });
    } catch {
      // The hook exposes the failure through `submitError`.
    }
  };

  if (isLoading) {
    return <Skeleton className="h-[480px] w-full rounded-xl" />;
  }

  if (error || !options) {
    return (
      <Card>
        <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-16 text-center text-sm">
          <Building2 className="h-6 w-6" />
          <p className="max-w-md">
            {error
              ? parseFrappeError(error)
              : "This unit cannot be booked right now."}
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {error ? (
              <Button
                variant="outline"
                size="sm"
                className="cursor-pointer"
                onClick={() => mutate()}
              >
                Try again
              </Button>
            ) : null}
            <Button asChild variant="outline" size="sm" className="cursor-pointer">
              <Link to={`/properties/${encodeURIComponent(property)}`}>
                Back to unit
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm" className="cursor-pointer">
              <Link to="/properties">Browse available properties</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (options.pending_booking) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Request already pending</CardTitle>
          <CardDescription>
            Your booking request for {options.property.property_name} is
            waiting for the property manager to confirm it.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button asChild className="cursor-pointer">
            <Link to="/bookings">View my booking request</Link>
          </Button>
          <Button asChild variant="outline" className="cursor-pointer">
            <Link to={`/properties/${encodeURIComponent(property)}`}>
              Back to unit
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-center gap-4 py-4">
          <div className="bg-muted flex h-16 w-20 items-center justify-center overflow-hidden rounded-lg">
            {options.property.cover_image ? (
              <img
                src={options.property.cover_image}
                alt={options.property.property_name}
                className="h-full w-full object-cover"
              />
            ) : (
              <Building2 className="text-muted-foreground h-5 w-5" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-semibold">{options.property.property_name}</p>
            <p className="text-muted-foreground text-sm">
              {[options.property.unit_number, options.property.location]
                .filter(Boolean)
                .join(" · ") || "Rental unit"}
            </p>
          </div>
          <p className="text-sm font-medium">
            {formatAmount(rent, options.currency)}
            <span className="text-muted-foreground font-normal"> / month</span>
          </p>
        </CardContent>
      </Card>

      <div className="flex items-center gap-2">
        {STEPS.map((label, index) => (
          <div key={label} className="flex flex-1 items-center gap-2">
            <span
              className={
                index <= step
                  ? "bg-primary text-primary-foreground flex h-6 w-6 items-center justify-center rounded-full text-xs"
                  : "bg-muted text-muted-foreground flex h-6 w-6 items-center justify-center rounded-full text-xs"
              }
            >
              {index + 1}
            </span>
            <span
              className={
                index === step ? "text-sm font-medium" : "text-muted-foreground text-sm"
              }
            >
              {label}
            </span>
          </div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{STEPS[step]}</CardTitle>
          <CardDescription>
            {step === 0
              ? "Choose when the tenancy starts and how long it runs."
              : step === 1
                ? "Confirm your details and add anything the manager should know."
                : "Review the booking before sending it to the property manager."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {step === 0 ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="start-date">Lease start</Label>
                <Input
                  id="start-date"
                  type="date"
                  value={effectiveStart}
                  onChange={(event) => {
                    setStartDate(event.target.value);
                    setEndDate("");
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contract-length">Contract length</Label>
                <NativeSelect
                  id="contract-length"
                  className="w-full"
                  value={effectiveMonths}
                  onChange={(event) => {
                    setMonths(Number(event.target.value));
                    setEndDate("");
                  }}
                >
                  {CONTRACT_LENGTHS.map((length) => (
                    <NativeSelectOption key={length} value={length}>
                      {length} months
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="end-date">Lease end</Label>
                <Input
                  id="end-date"
                  type="date"
                  value={computedEnd}
                  min={effectiveStart}
                  onChange={(event) => setEndDate(event.target.value)}
                />
                <p className="text-muted-foreground text-xs">
                  The end date follows the contract length until you change it.
                </p>
              </div>
              <div className="bg-muted/40 grid gap-2 rounded-lg p-4 text-sm sm:col-span-2 sm:grid-cols-3">
                <div>
                  <p className="text-muted-foreground text-xs">Monthly rent</p>
                  <p className="font-medium">
                    {formatAmount(rent, options.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">
                    Deposit ({options.deposit_months} month)
                  </p>
                  <p className="font-medium">
                    {formatAmount(deposit, options.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">
                    Estimated {effectiveMonths} months
                  </p>
                  <p className="font-medium">
                    {formatAmount(estimatedTotal, options.currency)}
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="space-y-4">
              <div className="bg-muted/40 grid gap-3 rounded-lg p-4 text-sm sm:grid-cols-2">
                <div>
                  <p className="text-muted-foreground text-xs">Customer</p>
                  <p className="font-medium">{options.customer.customer_name}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Name</p>
                  <p className="font-medium">{user?.fullName ?? "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Email</p>
                  <p className="font-medium">{user?.email ?? "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Booking date</p>
                  <p className="font-medium">{formatDate(new Date().toISOString())}</p>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="nrc">NRC / Passport number</Label>
                <Input
                  id="nrc"
                  value={nrc}
                  placeholder="Optional"
                  onChange={(event) => setNrc(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notes for the property manager</Label>
                <Textarea
                  id="notes"
                  rows={4}
                  value={notes}
                  placeholder="Move-in preferences, questions, special requests..."
                  onChange={(event) => setNotes(event.target.value)}
                />
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="grid gap-2 text-sm sm:grid-cols-2">
              <span className="text-muted-foreground">Unit</span>
              <span className="font-medium">{options.property.property_name}</span>
              <span className="text-muted-foreground">Lease</span>
              <span className="font-medium">
                {formatDate(effectiveStart)} → {formatDate(computedEnd)}
              </span>
              <span className="text-muted-foreground">Contract length</span>
              <span className="font-medium">{effectiveMonths} months</span>
              <span className="text-muted-foreground">Monthly rent</span>
              <span className="font-medium">
                {formatAmount(rent, options.currency)}
              </span>
              <span className="text-muted-foreground">
                Deposit ({options.deposit_months} month)
              </span>
              <span className="font-medium">
                {formatAmount(deposit, options.currency)}
              </span>
              <span className="text-muted-foreground">Estimated total</span>
              <span className="font-medium">
                {formatAmount(estimatedTotal, options.currency)}
              </span>
              {notes ? (
                <>
                  <span className="text-muted-foreground">Notes</span>
                  <span className="font-medium whitespace-pre-line">{notes}</span>
                </>
              ) : null}
            </div>
          ) : null}

          {validation ? (
            <Alert variant="destructive">
              <AlertDescription>{validation}</AlertDescription>
            </Alert>
          ) : null}

          {submitError ? (
            <Alert variant="destructive">
              <AlertDescription>
                {parseFrappeError(submitError)}
              </AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-2">
        <Button
          variant="outline"
          className="cursor-pointer"
          disabled={step === 0 || submitting}
          onClick={() => setStep((current) => Math.max(current - 1, 0))}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button className="cursor-pointer" onClick={goNext}>
            Continue
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button className="cursor-pointer" disabled={submitting} onClick={confirm}>
            {submitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 className="mr-2 h-4 w-4" />
            )}
            Send booking request
          </Button>
        )}
      </div>
    </div>
  );
}
