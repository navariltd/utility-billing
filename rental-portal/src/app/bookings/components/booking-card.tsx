/** One booking with its dates, status, documents and tenant actions. */

"use client";

import { PaymentDialog } from "@/components/payments/payment-dialog";
import { PropertyStatusBadge } from "@/components/properties";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatAmount, formatDate } from "@/lib/format";
import type { Booking } from "@/types/bookings";
import {
  Building2,
  CalendarDays,
  CreditCard,
  FileSignature,
  History,
  Pencil,
  PlusCircle,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ExtendBookingDialog,
  ModifyBookingDialog,
} from "./booking-action-dialogs";
import { CancelBookingDialog } from "./booking-cancel-dialog";
import { BookingHistoryDialog } from "./booking-history-dialog";
import { allocationTone, leaseLabel, leaseTone } from "./status";

interface BookingCardProps {
  booking: Booking;
  onChanged: () => void;
}

interface PaymentTarget {
  doctype: "Sales Invoice" | "Sales Order";
  name: string;
  amount: number;
  currency: string | null;
}

export function BookingCard({ booking, onChanged }: BookingCardProps) {
  const property = booking.properties[0];
  const [modifyOpen, setModifyOpen] = useState(false);
  const [extendOpen, setExtendOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [payment, setPayment] = useState<PaymentTarget | null>(null);

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="bg-muted flex h-14 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg">
              {property?.cover_image ? (
                <img
                  src={property.cover_image}
                  alt={property.property_name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <Building2 className="text-muted-foreground h-5 w-5" />
              )}
            </div>
            <div className="min-w-0">
              <CardTitle className="truncate text-base">
                {property?.property_name ?? booking.booking_reference}
              </CardTitle>
              <CardDescription>
                {booking.booking_reference}
                {property?.location ? ` · ${property.location}` : ""}
              </CardDescription>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <PropertyStatusBadge
              label={leaseLabel(booking.lease_status)}
              tone={leaseTone(booking.lease_status)}
            />
            {property ? (
              <PropertyStatusBadge
                label={property.allocation_status}
                tone={allocationTone(property.allocation_status)}
              />
            ) : null}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <div className="grid gap-2 sm:grid-cols-2">
          <span className="text-muted-foreground flex items-center gap-2">
            <CalendarDays className="h-4 w-4" />
            {formatDate(booking.start_date)} → {formatDate(booking.end_date)}
          </span>
          <span className="text-muted-foreground flex items-center gap-2">
            <FileSignature className="h-4 w-4" />
            {booking.contract
              ? `${booking.contract} · ${booking.contract_status || "Draft"}`
              : "Awaiting tenancy agreement"}
          </span>
        </div>

        {booking.notes ? (
          <p className="bg-muted/40 text-muted-foreground rounded-lg p-3 text-xs whitespace-pre-line">
            {booking.notes}
          </p>
        ) : null}

        {booking.documents.invoices.length > 0 ||
        booking.documents.orders.length > 0 ? (
          <div className="space-y-2">
            <Separator />
            {booking.documents.invoices.map((invoice) => (
              <div
                key={invoice.name}
                className="flex flex-wrap items-center justify-between gap-2"
              >
                <span>
                  <span className="font-medium">Invoice {invoice.name}</span>
                  <span className="text-muted-foreground">
                    {" "}
                    · due {formatDate(invoice.due_date)}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="font-medium">
                    {formatAmount(invoice.outstanding_amount, invoice.currency)}
                  </span>
                  {invoice.payable ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="cursor-pointer"
                      onClick={() =>
                        setPayment({
                          doctype: "Sales Invoice",
                          name: invoice.name,
                          amount: invoice.outstanding_amount,
                          currency: invoice.currency,
                        })
                      }
                    >
                      <CreditCard className="mr-2 h-4 w-4" />
                      Pay
                    </Button>
                  ) : null}
                </span>
              </div>
            ))}

            {booking.documents.orders.map((order) => (
              <div
                key={order.name}
                className="flex flex-wrap items-center justify-between gap-2"
              >
                <span>
                  <span className="font-medium">Order {order.name}</span>
                  <span className="text-muted-foreground">
                    {" "}
                    · {formatDate(order.transaction_date)}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="font-medium">
                    {formatAmount(order.payable_amount, order.currency)}
                  </span>
                  {order.payable ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="cursor-pointer"
                      onClick={() =>
                        setPayment({
                          doctype: "Sales Order",
                          name: order.name,
                          amount: order.payable_amount,
                          currency: order.currency,
                        })
                      }
                    >
                      <CreditCard className="mr-2 h-4 w-4" />
                      Pay
                    </Button>
                  ) : null}
                </span>
              </div>
            ))}
          </div>
        ) : null}

        <Separator />

        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm" variant="ghost" className="cursor-pointer">
            <Link
              to={`/properties/${encodeURIComponent(
                property?.utility_property ?? "",
              )}`}
            >
              <Building2 className="mr-2 h-4 w-4" />
              View unit
            </Link>
          </Button>
          {booking.can_modify ? (
            <Button
              size="sm"
              variant="outline"
              className="cursor-pointer"
              onClick={() => setModifyOpen(true)}
            >
              <Pencil className="mr-2 h-4 w-4" />
              Modify
            </Button>
          ) : null}
          {booking.can_extend ? (
            <Button
              size="sm"
              variant="outline"
              className="cursor-pointer"
              onClick={() => setExtendOpen(true)}
            >
              <PlusCircle className="mr-2 h-4 w-4" />
              Extend
            </Button>
          ) : null}
          {booking.can_cancel ? (
            <Button
              size="sm"
              variant="outline"
              className="cursor-pointer"
              onClick={() => setCancelOpen(true)}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          ) : null}
          <Button
            size="sm"
            variant="ghost"
            className="cursor-pointer"
            onClick={() => setHistoryOpen(true)}
          >
            <History className="mr-2 h-4 w-4" />
            History
          </Button>
        </div>
      </CardContent>

      <ModifyBookingDialog
        booking={booking}
        open={modifyOpen}
        onOpenChange={setModifyOpen}
        onSaved={onChanged}
      />
      <ExtendBookingDialog
        booking={booking}
        open={extendOpen}
        onOpenChange={setExtendOpen}
        onSaved={onChanged}
      />
      <CancelBookingDialog
        booking={booking}
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        onSaved={onChanged}
      />
      <BookingHistoryDialog
        name={booking.name}
        reference={booking.booking_reference}
        open={historyOpen}
        onOpenChange={setHistoryOpen}
      />

      {payment ? (
        <PaymentDialog
          open={Boolean(payment)}
          onOpenChange={(open) => {
            if (!open) {
              setPayment(null);
              onChanged();
            }
          }}
          referenceDoctype={payment.doctype}
          referenceName={payment.name}
          amount={payment.amount}
          currency={payment.currency}
          title="Pay tenancy charges"
        />
      ) : null}
    </Card>
  );
}
