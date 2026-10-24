/** Activity timeline of a single booking. */

"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";
import type { BookingDetailPayload } from "@/types/bookings";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Circle } from "lucide-react";

interface BookingHistoryDialogProps {
  name: string;
  reference: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface DetailResponse {
  message: BookingDetailPayload;
}

export function BookingHistoryDialog({
  name,
  reference,
  open,
  onOpenChange,
}: BookingHistoryDialogProps) {
  const { data, isLoading, error } = useFrappeGetCall<DetailResponse>(
    "utility_billing.api.portal.bookings.get_booking",
    { name },
    open ? `booking-detail-${name}` : null,
  );

  const timeline = data?.message?.timeline ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Booking history</DialogTitle>
          <DialogDescription>{reference}</DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : error ? (
          <p className="text-destructive text-sm">{error.message}</p>
        ) : timeline.length === 0 ? (
          <p className="text-muted-foreground text-sm">No activity yet.</p>
        ) : (
          <ol className="relative space-y-4 border-l pl-4">
            {timeline.map((event, index) => (
              <li key={`${event.date}-${index}`} className="relative">
                <Circle className="bg-background text-primary absolute top-1 -left-[22px] h-3 w-3 fill-current" />
                <p className="text-sm font-medium">{event.label}</p>
                <p className="text-muted-foreground text-xs">
                  {formatDateTime(event.date)}
                  {event.by ? ` · ${event.by}` : ""}
                </p>
              </li>
            ))}
          </ol>
        )}
      </DialogContent>
    </Dialog>
  );
}
