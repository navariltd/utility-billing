/** Second booking step: tenant identity and notes for the property manager. */

"use client";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatDate } from "@/lib/format";
import type { BookingOptions } from "@/types/bookings";
import { IdCard, Lock, Mail, MessageSquareText, User } from "lucide-react";
import { todayIso } from "./booking-dates";

const NOTES_LIMIT = 1000;

interface TenantDetailsStepProps {
  options: BookingOptions;
  fullName: string;
  email: string;
  nrc: string;
  notes: string;
  onNrcChange: (value: string) => void;
  onNotesChange: (value: string) => void;
}

/** Read-only account details plus the tenant-supplied identity fields. */
export function TenantDetailsStep({
  options,
  fullName,
  email,
  nrc,
  notes,
  onNrcChange,
  onNotesChange,
}: TenantDetailsStepProps) {
  return (
    <div className="space-y-6">
      <section className="bg-muted/40 grid gap-4 rounded-xl border p-4 sm:grid-cols-2">
        <div className="flex items-start gap-2">
          <User className="text-muted-foreground mt-0.5 h-4 w-4" />
          <div>
            <p className="text-muted-foreground text-xs">Tenant</p>
            <p className="text-sm font-medium">{fullName || "—"}</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Mail className="text-muted-foreground mt-0.5 h-4 w-4" />
          <div>
            <p className="text-muted-foreground text-xs">Email</p>
            <p className="text-sm font-medium">{email || "—"}</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <IdCard className="text-muted-foreground mt-0.5 h-4 w-4" />
          <div>
            <p className="text-muted-foreground text-xs">Customer</p>
            <p className="text-sm font-medium">
              {options.customer.customer_name}
            </p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <MessageSquareText className="text-muted-foreground mt-0.5 h-4 w-4" />
          <div>
            <p className="text-muted-foreground text-xs">Booking date</p>
            <p className="text-sm font-medium">{formatDate(todayIso())}</p>
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <Label htmlFor="nrc">NRC / Passport number</Label>
        <InputGroup>
          <InputGroupAddon align="inline-start">
            <IdCard />
          </InputGroupAddon>
          <InputGroupInput
            id="nrc"
            value={nrc}
            placeholder="Optional, but speeds up verification"
            onChange={(event) => onNrcChange(event.target.value)}
          />
        </InputGroup>
        <p className="text-muted-foreground text-xs">
          Used only to prepare your tenancy agreement.
        </p>
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <Label htmlFor="notes">Notes for the property manager</Label>
          <span className="text-muted-foreground text-xs">
            {notes.length}/{NOTES_LIMIT}
          </span>
        </div>
        <Textarea
          id="notes"
          rows={5}
          maxLength={NOTES_LIMIT}
          value={notes}
          placeholder="Move-in preferences, parking, questions, special requests..."
          onChange={(event) => onNotesChange(event.target.value)}
        />
      </section>

      <p className="text-muted-foreground flex items-start gap-2 text-xs">
        <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        Your details are shared with the property manager to review this
        request. Nothing is charged at this step.
      </p>
    </div>
  );
}
