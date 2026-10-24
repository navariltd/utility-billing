/**
 * Gateway selection and payment initiation.
 *
 * The server creates the ERPNext Payment Request and returns either a checkout
 * URL (redirect) or a phone-prompt confirmation for mobile money gateways.
 */

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
import { formatAmount } from "@/lib/format";
import type {
  PaymentGatewaysPayload,
  PaymentResult,
} from "@/types/payments";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import { CreditCard, Loader2, Smartphone } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

interface PaymentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  referenceDoctype: "Sales Invoice" | "Sales Order";
  referenceName: string;
  amount: number;
  currency?: string | null;
  title?: string;
}

interface GatewaysResponse {
  message: PaymentGatewaysPayload;
}

export function PaymentDialog({
  open,
  onOpenChange,
  referenceDoctype,
  referenceName,
  amount,
  currency,
  title,
}: PaymentDialogProps) {
  const { data, isLoading } = useFrappeGetCall<GatewaysResponse>(
    "utility_billing.api.portal.payments.get_payment_gateways",
    {},
    open ? "portal-payment-gateways" : null,
  );
  const { call, loading, error } = useFrappePostCall<PaymentResult>(
    "utility_billing.api.portal.payments.initiate_payment",
  );

  const gateways = useMemo(
    () => data?.message?.gateways ?? [],
    [data],
  );
  const [gatewayAccount, setGatewayAccount] = useState("");
  const [phone, setPhone] = useState("");
  const [sent, setSent] = useState<PaymentResult | null>(null);

  useEffect(() => {
    if (!open) {
      setSent(null);
      return;
    }
    if (!gatewayAccount && gateways.length > 0) {
      const preferred =
        gateways.find((gateway) => gateway.is_default && gateway.currency === currency) ??
        gateways.find((gateway) => gateway.currency === currency) ??
        gateways[0];
      setGatewayAccount(preferred.name);
    }
  }, [open, gateways, gatewayAccount, currency]);

  const selectedGateway = gateways.find((gateway) => gateway.name === gatewayAccount);
  const isPhone = selectedGateway?.channel === "Phone";

  const handlePay = async () => {
    setSent(null);
    try {
      const result = await call({
        reference_doctype: referenceDoctype,
        reference_name: referenceName,
        gateway_account: gatewayAccount || undefined,
        phone_number: isPhone ? phone : undefined,
        redirect_to: `${window.location.pathname}${window.location.search}`,
      });

      if (result.payment_url) {
        window.location.assign(result.payment_url);
        return;
      }

      setSent(result);
    } catch {
      // The hook exposes the failure through `error`.
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title ?? "Make a payment"}</DialogTitle>
          <DialogDescription>
            {referenceDoctype} {referenceName} · {formatAmount(amount, currency)}
          </DialogDescription>
        </DialogHeader>

        {sent ? (
          <div className="space-y-3">
            <Alert>
              <Smartphone className="h-4 w-4" />
              <AlertDescription>
                A payment prompt was sent. Approve it on your phone to complete
                the payment. Reference: {sent.payment_request}.
              </AlertDescription>
            </Alert>
            <p className="text-muted-foreground text-sm">
              The invoice stays open until your provider confirms the payment.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="payment-gateway">Payment method</Label>
              <NativeSelect
                id="payment-gateway"
                className="w-full"
                value={gatewayAccount}
                disabled={isLoading || gateways.length === 0}
                onChange={(event) => setGatewayAccount(event.target.value)}
              >
                {gateways.map((gateway) => (
                  <NativeSelectOption key={gateway.name} value={gateway.name}>
                    {gateway.label}
                    {gateway.currency ? ` · ${gateway.currency}` : ""}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
              {!isLoading && gateways.length === 0 ? (
                <p className="text-muted-foreground text-xs">
                  No payment gateway is configured for this company. Contact the
                  property manager.
                </p>
              ) : null}
            </div>

            {isPhone ? (
              <div className="space-y-2">
                <Label htmlFor="payment-phone">Phone number</Label>
                <Input
                  id="payment-phone"
                  inputMode="tel"
                  placeholder="07xx xxx xxx"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
                <p className="text-muted-foreground text-xs">
                  The payment prompt is sent to this number.
                </p>
              </div>
            ) : null}

            {error ? (
              <Alert variant="destructive">
                <AlertDescription>
                  {error.message || "Could not start the payment."}
                </AlertDescription>
              </Alert>
            ) : null}
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            className="cursor-pointer"
            onClick={() => onOpenChange(false)}
          >
            {sent ? "Close" : "Cancel"}
          </Button>
          {!sent ? (
            <Button
              className="cursor-pointer"
              disabled={
                loading || !gatewayAccount || (isPhone && phone.trim().length < 9)
              }
              onClick={handlePay}
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : isPhone ? (
                <Smartphone className="mr-2 h-4 w-4" />
              ) : (
                <CreditCard className="mr-2 h-4 w-4" />
              )}
              {isPhone ? "Send payment prompt" : "Continue to payment"}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
