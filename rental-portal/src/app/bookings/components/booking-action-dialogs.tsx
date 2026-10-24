/** Modify and extend dialogs for a booking. */

"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { formatDate } from "@/lib/format";
import type { Booking } from "@/types/bookings";
import { useFrappePostCall } from "frappe-react-sdk";
import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { errorMessage } from "./errors";

const EXTENSION_LENGTHS = [3, 6, 12, 24, 36];

export interface BookingDialogProps {
  booking: Booking;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

export function ModifyBookingDialog({
  booking,
  open,
  onOpenChange,
  onSaved,
}: BookingDialogProps) {
  const { call, loading } = useFrappePostCall<Booking>(
    "utility_billing.api.portal.bookings.modify_booking",
  );
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [months, setMonths] = useState(12);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setStartDate(booking.start_date ?? "");
    setEndDate(booking.end_date ?? "");
    setMonths(booking.contract_length_months ?? 12);
    setNotes(booking.notes ?? "");
    setError(null);
  }, [open, booking]);

  const save = async () => {
    setError(null);
    try {
      await call({
        name: booking.name,
        start_date: startDate,
        end_date: endDate || undefined,
        contract_length_months: endDate ? undefined : months,
        notes,
      });
      onSaved();
      onOpenChange(false);
    } catch (caught) {
      setError(errorMessage(caught, "The booking could not be updated."));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change booking dates</DialogTitle>
          <DialogDescription>
            {booking.booking_reference} · changes are possible until the tenancy
            agreement is created.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="modify-start">Lease start</Label>
            <Input
              id="modify-start"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="modify-months">Contract length</Label>
            <NativeSelect
              id="modify-months"
              className="w-full"
              value={months}
              disabled={Boolean(endDate)}
              onChange={(event) => setMonths(Number(event.target.value))}
            >
              {EXTENSION_LENGTHS.map((length) => (
                <NativeSelectOption key={length} value={length}>
                  {length} months
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="modify-end">Lease end</Label>
            <Input
              id="modify-end"
              type="date"
              value={endDate}
              min={startDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
            <p className="text-muted-foreground text-xs">
              Clear this field to use the contract length instead.
            </p>
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="modify-notes">Notes</Label>
            <Textarea
              id="modify-notes"
              rows={3}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </div>
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
            Cancel
          </Button>
          <Button className="cursor-pointer" disabled={loading} onClick={save}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ExtendBookingDialog({
  booking,
  open,
  onOpenChange,
  onSaved,
}: BookingDialogProps) {
  const { call, loading } = useFrappePostCall<Booking>(
    "utility_billing.api.portal.bookings.extend_booking",
  );
  const [months, setMonths] = useState(12);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setMonths(12);
    setNotes("");
    setError(null);
  }, [open]);

  const extend = async () => {
    setError(null);
    try {
      await call({
        name: booking.name,
        contract_length_months: months,
        notes: notes || undefined,
      });
      onSaved();
      onOpenChange(false);
    } catch (caught) {
      setError(errorMessage(caught, "The booking could not be extended."));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Extend booking</DialogTitle>
          <DialogDescription>
            {booking.contract
              ? `A renewal request will start on ${formatDate(
                  booking.end_date,
                )} after this lease ends.`
              : "The current lease end date will be moved."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="extend-months">Additional months</Label>
            <NativeSelect
              id="extend-months"
              className="w-full"
              value={months}
              onChange={(event) => setMonths(Number(event.target.value))}
            >
              {EXTENSION_LENGTHS.map((length) => (
                <NativeSelectOption key={length} value={length}>
                  {length} months
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </div>
          <div className="space-y-2">
            <Label htmlFor="extend-notes">Notes</Label>
            <Textarea
              id="extend-notes"
              rows={3}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </div>
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
            Cancel
          </Button>
          <Button className="cursor-pointer" disabled={loading} onClick={extend}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Extend
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
