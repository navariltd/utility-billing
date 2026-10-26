/**
 * Three step unit booking wizard: lease dates, tenant details, review.
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
import { useUser } from "@/contexts/user-context";
import type { Booking, BookingOptions } from "@/types/bookings";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import {
  ArrowLeft,
  ArrowRight,
  CalendarRange,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  UserRound,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { addMonthsToIso } from "./booking-dates";
import { BookingReviewStep } from "./booking-review-step";
import { BookingStepper, type BookingStep } from "./booking-stepper";
import {
  BookingWizardError,
  BookingWizardPending,
  BookingWizardSkeleton,
} from "./booking-states";
import { BookingSummary } from "./booking-summary";
import { LeaseDatesStep } from "./lease-dates-step";
import { TenantDetailsStep } from "./tenant-details-step";

const STEPS: BookingStep[] = [
  { label: "Dates", description: "Lease terms", icon: CalendarRange },
  { label: "Tenant", description: "Your details", icon: UserRound },
  { label: "Review", description: "Confirm request", icon: ClipboardCheck },
];

const STEP_COPY = [
  {
    title: "Plan your tenancy",
    description:
      "Choose when you move in and how long you want to stay. Costs update as you go.",
  },
  {
    title: "Tell us about you",
    description:
      "Confirm your contact details and add anything the property manager should know.",
  },
  {
    title: "Review your request",
    description:
      "Check the lease terms and costs before sending the request for approval.",
  },
];

interface BookingWizardProps {
  property: string;
}

interface OptionsResponse {
  message: BookingOptions;
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
  const [months, setMonths] = useState<number | null>(null);
  const [manualEndDate, setManualEndDate] = useState("");
  const [nrc, setNrc] = useState("");
  const [notes, setNotes] = useState("");
  const [validation, setValidation] = useState<string | null>(null);

  const effectiveStart = startDate || options?.default_start_date || "";
  const effectiveMonths =
    months ?? options?.default_contract_length_months ?? 12;
  const computedEnd = useMemo(
    () =>
      manualEndDate ||
      (effectiveStart ? addMonthsToIso(effectiveStart, effectiveMonths) : ""),
    [manualEndDate, effectiveStart, effectiveMonths],
  );

  const goToStep = (next: number) => {
    setValidation(null);
    setStep(Math.min(Math.max(next, 0), STEPS.length - 1));
  };

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
    goToStep(step + 1);
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
    return <BookingWizardSkeleton />;
  }

  if (error || !options) {
    return (
      <BookingWizardError
        property={property}
        error={error}
        onRetry={() => mutate()}
      />
    );
  }

  if (options.pending_booking) {
    return <BookingWizardPending property={property} options={options} />;
  }

  const copy = STEP_COPY[step];

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-4">
        <div className="space-y-1">
          <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            {options.property.property_name}
          </p>
          <h1 className="text-2xl font-semibold tracking-tight">
            Reserve your new home
          </h1>
          <p className="text-muted-foreground text-sm">
            Send a booking request in three quick steps. No payment is taken
            now.
          </p>
        </div>

        <BookingStepper
          steps={STEPS}
          current={step}
          onSelect={(index) => {
            if (index < step) goToStep(index);
          }}
        />

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{copy.title}</CardTitle>
            <CardDescription>{copy.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {step === 0 ? (
              <LeaseDatesStep
                options={options}
                startDate={effectiveStart}
                endDate={computedEnd}
                months={effectiveMonths}
                customEnd={Boolean(manualEndDate)}
                onStartDateChange={(value) => {
                  setStartDate(value);
                  setManualEndDate("");
                }}
                onMonthsChange={(value) => {
                  setMonths(value);
                  setManualEndDate("");
                }}
                onEndDateChange={(value) => setManualEndDate(value ?? "")}
              />
            ) : null}

            {step === 1 ? (
              <TenantDetailsStep
                options={options}
                fullName={user?.fullName ?? ""}
                email={user?.email ?? ""}
                nrc={nrc}
                notes={notes}
                onNrcChange={setNrc}
                onNotesChange={setNotes}
              />
            ) : null}

            {step === 2 ? (
              <BookingReviewStep
                options={options}
                startDate={effectiveStart}
                endDate={computedEnd}
                months={effectiveMonths}
                fullName={user?.fullName ?? ""}
                email={user?.email ?? ""}
                nrc={nrc}
                notes={notes}
              />
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
            onClick={() => goToStep(step - 1)}
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
            <Button
              className="cursor-pointer"
              disabled={submitting}
              onClick={confirm}
            >
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

      <BookingSummary
        options={options}
        startDate={effectiveStart}
        endDate={computedEnd}
        months={effectiveMonths}
      />
    </div>
  );
}
