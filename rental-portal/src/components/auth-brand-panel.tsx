"use client";

/**
 * Brand panel shown next to the auth forms on wide screens.
 *
 * Colours come from the active theme preset (`primary` plus an `accent` glow),
 * so the sign in and sign up pages follow the same theme as the portal.
 */

import { Logo } from "@/components/logo";
import { FileText, Home, ShieldCheck } from "lucide-react";

const HIGHLIGHTS = [
  { label: "Browse available units", icon: Home },
  { label: "Invoices and utility bills", icon: FileText },
  { label: "Tenant-first security", icon: ShieldCheck },
];

interface AuthBrandPanelProps {
  title: string;
  description: string;
}

export function AuthBrandPanel({ title, description }: AuthBrandPanelProps) {
  return (
    <div className="bg-primary bg-brand-gradient relative hidden overflow-hidden md:block">
      <div className="bg-accent pointer-events-none absolute -top-24 -right-24 size-72 rounded-full opacity-30 blur-3xl" />
      <div className="bg-accent pointer-events-none absolute -bottom-32 -left-20 size-72 rounded-full opacity-20 blur-3xl" />

      <div className="text-primary-foreground relative flex h-full flex-col justify-between gap-8 p-8">
        <div className="flex items-center gap-2">
          <span className="bg-primary-foreground/15 flex size-9 items-center justify-center rounded-md">
            <Logo size={22} />
          </span>
          <span className="text-sm font-semibold tracking-wide">
            Rental Billing
          </span>
        </div>

        <div className="space-y-4">
          <h2 className="text-2xl leading-tight font-semibold">{title}</h2>
          <p className="text-primary-foreground/80 text-sm">{description}</p>
          <ul className="space-y-2 text-sm">
            {HIGHLIGHTS.map((item) => (
              <li key={item.label} className="flex items-center gap-2">
                <item.icon className="size-4 shrink-0" />
                <span>{item.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-primary-foreground/70 text-xs">
          Utilities, rent and tenancy records in one place.
        </p>
      </div>
    </div>
  );
}
