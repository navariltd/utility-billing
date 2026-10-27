/**
 * Gateway selection and payment initiation.
 *
 * The server asks the gateway for a checkout URL and returns it; the dialog
 * redirects straight to that URL. No Payment Request is created, mirroring the
 * event booking flow.
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
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { formatAmount } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  PaymentGatewaysPayload,
  PaymentLinkResult,
} from "@/types/payments";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import {
  CreditCard,
  ExternalLink,
  Loader2,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
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
  const { call, loading, error } = useFrappePostCall<PaymentLinkResult>(
    "utility_billing.api.portal.payments.initiate_payment",
  );

  const gateways = useMemo(() => data?.message?.gateways ?? [], [data]);
  const [gatewayAccount, setGatewayAccount] = useState("");
  const [linkError, setLinkError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setLinkError(null);
      return;
    }
    if (!gatewayAccount && gateways.length > 0) {
      const preferred =
        gateways.find(
          (gateway) => gateway.is_default && gateway.currency === currency,
        ) ??
        gateways.find((gateway) => gateway.currency === currency) ??
        gateways[0];
      setGatewayAccount(preferred.name);
    }
  }, [open, gateways, gatewayAccount, currency]);

  const handlePay = async () => {
    setLinkError(null);
    try {
      const result = await call({
        reference_doctype: referenceDoctype,
        reference_name: referenceName,
        gateway_account: gatewayAccount || undefined,
        redirect_to: `${window.location.pathname}${window.location.search}`,
      });

      // Frappe API calls return the response inside `.message`
      const paymentUrl =
        result?.payment_url || (result as any)?.message?.payment_url;

      if (paymentUrl) {
        window.location.assign(paymentUrl);
        return;
      }

      setLinkError("The payment provider did not return a checkout page.");
    } catch {
      // The hook exposes the failure through `error`.
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{title ?? "Make a payment"}</DialogTitle>
          <DialogDescription>
            {referenceDoctype} {referenceName}
          </DialogDescription>
        </DialogHeader>

        <div className="bg-muted/40 flex items-center justify-between rounded-xl border px-4 py-3">
          <div>
            <p className="text-muted-foreground text-xs">Amount due</p>
            <p className="text-xl font-semibold">
              {formatAmount(amount, currency)}
            </p>
          </div>
          <ShieldCheck className="text-muted-foreground h-6 w-6" />
        </div>

        <div className="space-y-3">
          <Label>Payment method</Label>
          <RadioGroup
            value={gatewayAccount}
            onValueChange={setGatewayAccount}
            disabled={isLoading || gateways.length === 0}
          >
            {gateways.map((gateway) => {
              const selected = gateway.name === gatewayAccount;
              const Icon =
                gateway.channel === "Phone" ? Smartphone : CreditCard;

              return (
                <Label
                  key={gateway.name}
                  htmlFor={`gateway-${gateway.name}`}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors",
                    selected
                      ? "border-primary bg-primary/5"
                      : "hover:bg-muted/50",
                  )}
                >
                  <RadioGroupItem
                    id={`gateway-${gateway.name}`}
                    value={gateway.name}
                    className="mt-0.5"
                  />
                  <span className="bg-background flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium">
                      {gateway.label}
                    </span>
                    <span className="text-muted-foreground block text-xs">
                      {gateway.channel === "Phone"
                        ? "Approve the prompt on your phone"
                        : "Pay on the provider's secure page"}
                      {gateway.currency ? ` · ${gateway.currency}` : ""}
                    </span>
                    {gateway.message ? (
                      <span className="text-muted-foreground mt-1 block text-xs">
                        {gateway.message}
                      </span>
                    ) : null}
                  </span>
                </Label>
              );
            })}
          </RadioGroup>

          {isLoading ? (
            <p className="text-muted-foreground flex items-center gap-2 text-xs">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading payment methods...
            </p>
          ) : null}

          {!isLoading && gateways.length === 0 ? (
            <p className="text-muted-foreground text-xs">
              No payment gateway is configured for this company. Contact the
              property manager.
            </p>
          ) : null}
        </div>

        {error || linkError ? (
          <Alert variant="destructive">
            <AlertDescription>
              {error?.message || linkError || "Could not start the payment."}
            </AlertDescription>
          </Alert>
        ) : null}

        <p className="text-muted-foreground flex items-center gap-2 text-xs">
          <ShieldCheck className="h-3.5 w-3.5" />
          You will be redirected to the provider to complete the payment
          securely.
        </p>

        <DialogFooter>
          <Button
            variant="outline"
            className="cursor-pointer"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            className="cursor-pointer"
            disabled={loading || !gatewayAccount || gateways.length === 0}
            onClick={handlePay}
          >
            {loading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ExternalLink className="mr-2 h-4 w-4" />
            )}
            Continue to payment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
