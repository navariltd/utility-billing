/** A Pay button that opens its own gateway dialog. */

"use client";

import { Button } from "@/components/ui/button";
import { CreditCard } from "lucide-react";
import { useState } from "react";
import { PaymentDialog } from "./payment-dialog";

interface PayButtonProps {
  referenceDoctype: "Sales Invoice" | "Sales Order";
  referenceName: string;
  amount: number;
  currency?: string | null;
  label?: string;
}

export function PayButton({
  referenceDoctype,
  referenceName,
  amount,
  currency,
  label = "Pay",
}: PayButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        className="cursor-pointer"
        onClick={() => setOpen(true)}
      >
        <CreditCard className="mr-2 h-4 w-4" />
        {label}
      </Button>
      <PaymentDialog
        open={open}
        onOpenChange={setOpen}
        referenceDoctype={referenceDoctype}
        referenceName={referenceName}
        amount={amount}
        currency={currency}
      />
    </>
  );
}
