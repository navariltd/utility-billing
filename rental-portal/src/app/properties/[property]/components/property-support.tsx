/**
 * Support card on an active property page.
 *
 * Shows the open/resolved totals and the latest tickets for the unit, and
 * opens the shared support dialog for raising a request or following replies.
 */

"use client";

import { SupportDialog } from "@/components/support/support-dialog";
import { supportStatusClass } from "@/components/support/support-utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import type { SupportPayload } from "@/types/support";
import { useFrappeGetCall } from "frappe-react-sdk";
import { ChevronRight, LifeBuoy, Plus } from "lucide-react";
import { useState } from "react";

const LIST_REFRESH_MS = 60000;
const LATEST_LIMIT = 3;

interface PropertySupportProps {
  property: string;
  reference: string;
  propertyName?: string | null;
}

export function PropertySupport({
  property,
  reference,
  propertyName,
}: PropertySupportProps) {
  const [open, setOpen] = useState(false);
  const [startView, setStartView] = useState<"list" | "create">("list");
  const [initialIssue, setInitialIssue] = useState<string | null>(null);

  const { data, isLoading, error, mutate } = useFrappeGetCall<{
    message: SupportPayload;
  }>(
    "utility_billing.api.portal.support.get_property_support",
    { property },
    `property-support-${property}`,
    { refreshInterval: LIST_REFRESH_MS },
  );

  const payload = data?.message;
  const issues = payload?.issues ?? [];
  const latest = issues.slice(0, LATEST_LIMIT);
  const supportReference = payload?.context.reference ?? reference;

  const showDialog = (view: "list" | "create", issue?: string) => {
    setStartView(view);
    setInitialIssue(issue ?? null);
    setOpen(true);
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-base">
              <LifeBuoy className="text-primary h-4 w-4" />
              Support
            </CardTitle>
            <CardDescription>
              Report a problem with this unit and follow every reply and status
              change in one place.
            </CardDescription>
          </div>
          <Button
            size="sm"
            className="cursor-pointer"
            onClick={() => showDialog("create")}
          >
            <Plus className="mr-1.5 h-4 w-4" />
            Raise a request
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading && !payload ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : null}

          {error ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-dashed px-4 py-3">
              <p className="text-muted-foreground text-sm">
                {error.message || "Could not load your support requests."}
              </p>
              <Button
                size="sm"
                variant="outline"
                className="cursor-pointer"
                onClick={() => void mutate()}
              >
                Try again
              </Button>
            </div>
          ) : null}

          {payload && issues.length === 0 ? (
            <p className="text-muted-foreground rounded-lg border border-dashed px-4 py-6 text-center text-sm">
              No support requests yet. Tell us about any maintenance, billing or
              access issue with this unit.
            </p>
          ) : null}

          {payload && issues.length > 0 ? (
            <>
              <div className="flex flex-wrap gap-2 text-xs">
                <Badge variant="outline">{payload.counts.open} open</Badge>
                <Badge variant="outline">{payload.counts.replied} replied</Badge>
                <Badge variant="outline">{payload.counts.resolved} resolved</Badge>
              </div>

              <ul className="divide-y rounded-lg border">
                {latest.map((issue) => (
                  <li key={issue.name}>
                    <button
                      type="button"
                      className="hover:bg-muted/50 focus-visible:ring-ring group flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none"
                      onClick={() => showDialog("list", issue.name)}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge
                            variant="outline"
                            className={supportStatusClass(issue.status)}
                          >
                            {issue.status}
                          </Badge>
                          <span className="text-muted-foreground text-xs">
                            {issue.name} · {formatDate(issue.creation)}
                          </span>
                        </div>
                        <p className="mt-1 truncate text-sm font-medium">
                          {issue.subject}
                        </p>
                      </div>
                      <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
                    </button>
                  </li>
                ))}
              </ul>

              {issues.length > LATEST_LIMIT ? (
                <Button
                  size="sm"
                  variant="ghost"
                  className="cursor-pointer"
                  onClick={() => showDialog("list")}
                >
                  View all {issues.length} requests
                </Button>
              ) : null}
            </>
          ) : null}
        </CardContent>
      </Card>

      <SupportDialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) {
            setInitialIssue(null);
            setStartView("list");
          }
        }}
        property={property}
        reference={supportReference}
        propertyName={propertyName}
        initialIssue={initialIssue}
        startView={startView}
      />
    </>
  );
}
