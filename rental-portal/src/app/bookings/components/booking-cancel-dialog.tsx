/** Cancellation confirmation for a booking. */

"use client";

import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Booking } from "@/types/bookings";
import { useFrappePostCall } from "frappe-react-sdk";
import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { errorMessage } from "./errors";

interface CancelBookingDialogProps {
  booking: Booking;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

export function CancelBookingDialog({
  booking,
  open,
  onOpenChange,
  onSaved,
}: CancelBookingDialogProps) {
  const { call, loading } = useFrappePostCall<Booking>(
    "utility_billing.api.portal.bookings.cancel_booking",
  );
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setReason("");
    setError(null);
  }, [open]);

  const cancelBooking = async () => {
    setError(null);
    try {
      await call({ name: booking.name, reason: reason || undefined });
      onSaved();
      onOpenChange(false);
    } catch (caught) {
      setError(errorMessage(caught, "The booking could not be cancelled."));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cancel booking</DialogTitle>
          <DialogDescription>
            {booking.booking_reference} will be cancelled and the unit released.
          </DialogDescription>
        </DialogHeader>

        <Alert variant="destructive">
          <AlertDescription>
            This cannot be undone from the portal. A manager can raise a new
            request if you change your mind.
          </AlertDescription>
        </Alert>

        <div className="space-y-2">
          <Label htmlFor="cancel-reason">Reason (optional)</Label>
          <Textarea
            id="cancel-reason"
            rows={3}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>

        {error ? (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <DialogFooter>
          <Button
            variant="outline"
            className="cursor-pointer"
            onClick={() => onOpenChange(false)}
          >
            Keep booking
          </Button>
          <Button
            variant="destructive"
            className="cursor-pointer"
            disabled={loading}
            onClick={cancelBooking}
          >
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Cancel booking
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
