/** Detail view for one support ticket with conversation and resolution. */

"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatDateTime } from "@/lib/format";
import type { SupportIssue, SupportTimelineEvent } from "@/types/support";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Clock3,
  MessageSquare,
  RefreshCw,
} from "lucide-react";
import type { ReactNode } from "react";
import { SupportReplyForm } from "./support-reply-form";
import { SupportTimeline } from "./support-timeline";
import { formatSupportDuration, supportStatusClass } from "./support-utils";

interface SupportDetailProps {
  issue: SupportIssue | null;
  timeline: SupportTimelineEvent[];
  isLoading: boolean;
  error?: { message?: string } | null;
  onBack: () => void;
  onRetry: () => void;
  onReplied: (timeline: SupportTimelineEvent[]) => void;
}

export function SupportDetail({
  issue,
  timeline,
  isLoading,
  error,
  onBack,
  onRetry,
  onReplied,
}: SupportDetailProps) {
  if (isLoading && !issue) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  if (error || !issue) {
    return (
      <div className="space-y-4">
        <BackButton onBack={onBack} />
        <Alert variant="destructive">
          <AlertDescription>
            {error?.message || "This support request could not be loaded."}
          </AlertDescription>
        </Alert>
        <Button size="sm" variant="outline" className="cursor-pointer" onClick={onRetry}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <BackButton onBack={onBack} />
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className={supportStatusClass(issue.status)}>
              {issue.status}
            </Badge>
            <span className="text-muted-foreground text-xs">{issue.name}</span>
          </div>
          <h3 className="text-lg leading-tight font-semibold">{issue.subject}</h3>
        </div>
        <Button
          size="sm"
          variant="ghost"
          className="cursor-pointer"
          onClick={onRetry}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetaTile
          icon={<CalendarDays className="h-3.5 w-3.5" />}
          label="Opened"
          value={formatDate(issue.opening_date || issue.creation)}
        />
        <MetaTile
          icon={<Clock3 className="h-3.5 w-3.5" />}
          label="First response"
          value={
            issue.first_responded_on
              ? formatDateTime(issue.first_responded_on)
              : "Awaiting response"
          }
        />
        <MetaTile
          icon={<RefreshCw className="h-3.5 w-3.5" />}
          label="Last update"
          value={issue.modified ? formatDateTime(issue.modified) : "—"}
        />
        <MetaTile
          icon={<CheckCircle2 className="h-3.5 w-3.5" />}
          label="Resolution time"
          value={formatSupportDuration(issue.resolution_time)}
        />
      </div>

      <section className="space-y-2">
        <h4 className="text-sm font-medium">Request</h4>
        {issue.description ? (
          <div
            className="bg-muted/30 space-y-1 rounded-xl border px-4 py-3 text-sm [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:leading-relaxed [&_ul]:list-disc [&_ul]:pl-5"
            dangerouslySetInnerHTML={{ __html: issue.description }}
          />
        ) : (
          <p className="bg-muted/30 text-muted-foreground rounded-xl border px-4 py-3 text-sm">
            {issue.snippet || "No description was provided."}
          </p>
        )}
        <p className="text-muted-foreground text-xs">
          Raised {formatDateTime(issue.creation)}
          {issue.customer_name ? ` by ${issue.customer_name}` : ""}
          {issue.service_request ? ` · linked to ${issue.service_request}` : ""}
        </p>
      </section>

      {issue.resolution_details || !issue.is_open ? (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="mb-2 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h4 className="text-sm font-medium">Resolution</h4>
            <span className="text-muted-foreground text-xs">
              {formatSupportDuration(issue.resolution_time)}
            </span>
          </div>
          {issue.resolution_details ? (
            <div
              className="space-y-1 text-sm [&_a]:underline [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:leading-relaxed [&_ul]:list-disc [&_ul]:pl-5"
              dangerouslySetInnerHTML={{ __html: issue.resolution_details }}
            />
          ) : (
            <p className="text-muted-foreground text-sm">
              This request is marked {issue.status.toLowerCase()}. Reply below if you
              need more help.
            </p>
          )}
        </section>
      ) : null}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <MessageSquare className="text-muted-foreground h-4 w-4" />
          <h4 className="text-sm font-medium">Conversation & updates</h4>
          <span className="text-muted-foreground text-xs">
            Refreshes automatically
          </span>
        </div>
        <SupportTimeline events={timeline} />
      </section>

      <SupportReplyForm
        issue={issue.name}
        isResolved={!issue.is_open}
        onReplied={onReplied}
      />
    </div>
  );
}

function BackButton({ onBack }: { onBack: () => void }) {
  return (
    <Button
      type="button"
      size="sm"
      variant="ghost"
      className="-ml-2 cursor-pointer"
      onClick={onBack}
    >
      <ArrowLeft className="mr-2 h-4 w-4" />
      All requests
    </Button>
  );
}

function MetaTile({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="bg-muted/30 rounded-lg border p-3">
      <p className="text-muted-foreground flex items-center gap-1.5 text-xs">
        {icon}
        {label}
      </p>
      <div className="mt-1 text-sm font-medium">{value}</div>
    </div>
  );
}
