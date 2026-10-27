/** Loading, error and already-pending states of the booking wizard. */

"use client";

import { parseFrappeError } from "@/components/doctype/form/parse-error";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { BookingOptions } from "@/types/bookings";
import { Building2, Clock3 } from "lucide-react";
import { Link } from "react-router-dom";

/** Placeholder that matches the wizard layout while options load. */
export function BookingWizardSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="space-y-4">
        <Skeleton className="h-2 w-full rounded-full" />
        <Skeleton className="h-16 w-full rounded-xl" />
        <Skeleton className="h-[420px] w-full rounded-xl" />
      </div>
      <Skeleton className="hidden h-[520px] w-full rounded-xl lg:block" />
    </div>
  );
}

/** Error state with retry and navigation options. */
export function BookingWizardError({
  property,
  error,
  onRetry,
}: {
  property: string;
  error: unknown;
  onRetry: () => void;
}) {
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
              onClick={onRetry}
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

/** State shown when the tenant already has an open request for the unit. */
export function BookingWizardPending({
  property,
  options,
}: {
  property: string;
  options: BookingOptions;
}) {
  return (
    <Card className="mx-auto max-w-2xl">
      <CardHeader>
        <div className="bg-primary/10 text-primary mb-2 flex h-11 w-11 items-center justify-center rounded-full">
          <Clock3 className="h-5 w-5" />
        </div>
        <CardTitle>Request already pending</CardTitle>
        <CardDescription>
          Your booking request for {options.property.property_name} is waiting
          for the property manager to confirm it.
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
