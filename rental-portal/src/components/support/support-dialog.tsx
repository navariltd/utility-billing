/**
 * Support centre shared by the bookings page and an active property page.
 *
 * Tickets are scoped either to a booking or to a property tenancy. The list and
 * detail are polled while the dialog is open so staff replies, status changes
 * and resolution details appear without a manual refresh.
 */

"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type {
  SupportIssuePayload,
  SupportPayload,
  SupportTimelineEvent,
} from "@/types/support";
import { useFrappeGetCall } from "frappe-react-sdk";
import { LifeBuoy } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { SupportCreateForm } from "./support-create-form";
import { SupportDetail } from "./support-detail";
import { SupportList } from "./support-list";

type View = "list" | "create" | "detail";

interface SupportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  booking?: string;
  property?: string;
  reference: string;
  propertyName?: string | null;
  initialIssue?: string | null;
  startView?: View;
}

interface SupportResponse {
  message: SupportPayload;
}

const LIST_REFRESH_MS = 30000;
const DETAIL_REFRESH_MS = 15000;

export function SupportDialog({
  open,
  onOpenChange,
  booking,
  property,
  reference,
  propertyName,
  initialIssue,
  startView = "list",
}: SupportDialogProps) {
  const [view, setView] = useState<View>("list");
  const [selected, setSelected] = useState<string | null>(null);
  const isProperty = Boolean(property);
  const scope = property ?? booking ?? "";

  const {
    data: listData,
    isLoading: listLoading,
    error: listError,
    mutate: mutateList,
  } = useFrappeGetCall<SupportResponse>(
    isProperty
      ? "utility_billing.api.portal.support.get_property_support"
      : "utility_billing.api.portal.support.get_booking_support",
    isProperty ? { property } : { booking },
    open && scope
      ? `${isProperty ? "property" : "booking"}-support-${scope}`
      : null,
    { refreshInterval: open ? LIST_REFRESH_MS : 0 },
  );

  const {
    data: detailData,
    isLoading: detailLoading,
    error: detailError,
    mutate: mutateDetail,
  } = useFrappeGetCall<{ message: SupportIssuePayload }>(
    "utility_billing.api.portal.support.get_support_issue",
    { issue: selected ?? "" },
    open && view === "detail" && selected
      ? `support-issue-${selected}`
      : null,
    {
      refreshInterval:
        open && view === "detail" && selected ? DETAIL_REFRESH_MS : 0,
    },
  );

  useEffect(() => {
    if (!open) {
      setView("list");
      setSelected(null);
      return;
    }
    if (initialIssue) {
      setSelected(initialIssue);
      setView("detail");
      return;
    }
    setView(startView);
  }, [open, initialIssue, startView]);

  const payload = listData?.message;
  const ticket = detailData?.message;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="gap-0 overflow-hidden p-0 sm:max-w-3xl">
        <DialogHeader className="border-b px-6 py-4 pr-12">
          <div className="flex items-start gap-3">
            <div className="bg-primary/10 text-primary rounded-lg p-2">
              <LifeBuoy className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <DialogTitle>Support</DialogTitle>
              <DialogDescription className="truncate">
                {propertyName ? `${propertyName} · ` : ""}
                {reference}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          {view === "list" ? (
            <SupportList
              issues={payload?.issues ?? []}
              counts={
                payload?.counts ?? { open: 0, replied: 0, resolved: 0, total: 0 }
              }
              isLoading={listLoading}
              error={listError}
              onRetry={() => void mutateList()}
              onSelect={(name) => {
                setSelected(name);
                setView("detail");
              }}
              onCreate={() => setView("create")}
            />
          ) : null}

          {view === "create" ? (
            <SupportCreateForm
              booking={booking}
              property={property}
              onCancel={() => setView("list")}
              onCreated={(created) => {
                setSelected(created.issue.name);
                setView("detail");
                void mutateList();
                toast.success(
                  `${created.issue.name} raised. We will follow up shortly.`,
                );
              }}
            />
          ) : null}

          {view === "detail" ? (
            <SupportDetail
              issue={ticket?.issue ?? null}
              timeline={ticket?.timeline ?? []}
              isLoading={detailLoading}
              error={detailError}
              onBack={() => {
                setView("list");
                setSelected(null);
              }}
              onRetry={() => {
                void mutateDetail();
                void mutateList();
              }}
              onReplied={(timeline: SupportTimelineEvent[]) => {
                void mutateDetail(
                  ticket ? { message: { ...ticket, timeline } } : undefined,
                  { revalidate: true },
                );
                void mutateList();
              }}
            />
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
