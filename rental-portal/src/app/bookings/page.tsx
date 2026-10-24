/**
 * My bookings: current reservations and tenancies, plus past bookings.
 *
 * Each card shows the derived lease status, linked payable documents and the
 * actions still allowed on the booking (modify, extend, cancel, history).
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { BookingsPayload } from "@/types/bookings";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Building2, Home } from "lucide-react";
import { Link } from "react-router-dom";
import { BookingCard } from "./components/booking-card";

interface BookingsResponse {
  message: BookingsPayload;
}

export default function BookingsPage() {
  const { data, isLoading, error, mutate } = useFrappeGetCall<BookingsResponse>(
    "utility_billing.api.portal.bookings.get_my_bookings",
    {},
    "portal-my-bookings",
  );

  const payload = data?.message;
  const current = payload?.current ?? [];
  const history = payload?.history ?? [];

  return (
    <BaseLayout
      title="My Bookings"
      description={
        payload?.customer
          ? `Reservations and tenancies for ${payload.customer}`
          : "Your reservations and tenancies"
      }
    >
      <div className="space-y-4 px-4 lg:px-6">
        {error ? (
          <Card>
            <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-12 text-sm">
              <Home className="h-6 w-6" />
              {error.message || "Could not load your bookings."}
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
          <Tabs defaultValue="current" className="space-y-4">
            <TabsList>
              <TabsTrigger value="current" className="cursor-pointer">
                Current ({payload?.counts.current ?? 0})
              </TabsTrigger>
              <TabsTrigger value="history" className="cursor-pointer">
                History ({payload?.counts.history ?? 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="current" className="space-y-4">
              {isLoading ? (
                <BookingSkeletons />
              ) : current.length === 0 ? (
                <EmptyBookings message="You have no current bookings." />
              ) : (
                current.map((booking) => (
                  <BookingCard
                    key={booking.name}
                    booking={booking}
                    onChanged={mutate}
                  />
                ))
              )}
            </TabsContent>

            <TabsContent value="history" className="space-y-4">
              {isLoading ? (
                <BookingSkeletons />
              ) : history.length === 0 ? (
                <EmptyBookings message="No past bookings were found." />
              ) : (
                history.map((booking) => (
                  <BookingCard
                    key={booking.name}
                    booking={booking}
                    onChanged={mutate}
                  />
                ))
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>
    </BaseLayout>
  );
}

function BookingSkeletons() {
  return (
    <div className="space-y-4">
      {[1, 2].map((index) => (
        <Skeleton key={index} className="h-56 w-full rounded-xl" />
      ))}
    </div>
  );
}

function EmptyBookings({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="text-muted-foreground flex flex-col items-center gap-3 py-12 text-sm">
        <Building2 className="h-6 w-6" />
        {message}
        <Button asChild variant="outline" size="sm" className="cursor-pointer">
          <Link to="/properties">Browse available properties</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
