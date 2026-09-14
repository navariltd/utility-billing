/**
 * Portal dashboard.
 *
 * Phase 1 shows the signed in user's identity and a summary of the units linked
 * to their tenancy. Role specific dashboards (landlord, property manager) are
 * added in a later phase.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortal } from "@/contexts/portal-context";
import { useUser } from "@/contexts/user-context";
import type { TenantProperties } from "@/types/portal";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Building2, CheckCircle2, History } from "lucide-react";
import { Link } from "react-router-dom";

interface TenantPropertiesResponse {
  message: TenantProperties;
}

export default function DashboardPage() {
  const { user } = useUser();
  const { portalRole, portal } = usePortal();

  const { data, isLoading } = useFrappeGetCall<TenantPropertiesResponse>(
    "utility_billing.api.portal.properties.get_my_properties",
  );

  const current = data?.message?.current ?? [];
  const history = data?.message?.history ?? [];
  const reserved = current.filter((property) => property.state === "Reserved");

  const stats = [
    {
      title: "Current Units",
      value: current.length - reserved.length,
      icon: CheckCircle2,
      description: "Signed tenancies",
    },
    {
      title: "Reserved",
      value: reserved.length,
      icon: Building2,
      description: "Awaiting signature",
    },
    {
      title: "History",
      value: history.length,
      icon: History,
      description: "Past tenancies",
    },
  ];

  return (
    <BaseLayout
      title={`Welcome, ${user?.fullName ?? "there"}`}
      description={
        portal?.customer
          ? `You are signed in as ${portalRole} for ${portal.customer}`
          : "Your rental portal overview"
      }
    >
      <div className="space-y-6 px-4 lg:px-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{portalRole} Portal</Badge>
          {user?.email ? (
            <span className="text-muted-foreground text-sm">{user.email}</span>
          ) : null}
        </div>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-28 w-full rounded-lg" />
            <Skeleton className="h-28 w-full rounded-lg" />
            <Skeleton className="h-28 w-full rounded-lg" />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {stats.map((stat) => (
              <Card key={stat.title}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <CardTitle className="text-sm font-medium">
                    {stat.title}
                  </CardTitle>
                  <stat.icon className="text-muted-foreground h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <CardDescription>{stat.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Getting started</CardTitle>
            <CardDescription>
              Invoices, payments and maintenance requests are being rolled out
              next.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4 text-sm">
            <Link to="/my-properties" className="text-primary underline underline-offset-4">
              View my properties
            </Link>
            <Link to="/properties" className="text-primary underline underline-offset-4">
              Browse available properties
            </Link>
            {user ? (
              <Link
                to={`/app/user/${encodeURIComponent(user.name)}`}
                className="text-primary underline underline-offset-4"
              >
                My profile
              </Link>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </BaseLayout>
  );
}

