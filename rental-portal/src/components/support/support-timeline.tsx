/** Conversation and status timeline for a support ticket. */

"use client";

import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";
import type { SupportTimelineEvent } from "@/types/support";
import { ArrowRight, CircleDot, Headset } from "lucide-react";
import { supportInitials } from "./support-utils";

interface SupportTimelineProps {
  events: SupportTimelineEvent[];
}

export function SupportTimeline({ events }: SupportTimelineProps) {
  if (events.length === 0) {
    return (
      <p className="text-muted-foreground py-6 text-center text-sm">
        No activity on this request yet.
      </p>
    );
  }

  return (
    <ol className="space-y-4">
      {events.map((event) => {
        if (event.type === "created") {
          return (
            <li key={event.id} className="flex items-center gap-2">
              <span className="bg-border h-px flex-1" />
              <span className="text-muted-foreground flex items-center gap-1.5 text-xs">
                <CircleDot className="h-3.5 w-3.5" />
                Request raised · {formatDateTime(event.date)}
              </span>
              <span className="bg-border h-px flex-1" />
            </li>
          );
        }

        if (event.type === "status") {
          return (
            <li key={event.id} className="flex justify-center">
              <div className="bg-muted/60 flex max-w-full flex-wrap items-center justify-center gap-1.5 rounded-full border px-3 py-1.5 text-xs">
                <span className="font-medium">{event.label}</span>
                <span className="text-muted-foreground">{event.old_value}</span>
                <ArrowRight className="text-muted-foreground h-3 w-3" />
                <span className="font-medium">{event.new_value}</span>
                <span className="text-muted-foreground">
                  · {formatDateTime(event.date)}
                  {event.author ? ` · ${event.author}` : ""}
                </span>
              </div>
            </li>
          );
        }

        const isCustomer = event.author_type === "customer";

        return (
          <li
            key={event.id}
            className={cn("flex items-start gap-3", isCustomer && "flex-row-reverse")}
          >
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                isCustomer
                  ? "bg-primary/10 text-primary border-primary/20"
                  : "bg-muted text-muted-foreground",
              )}
              aria-hidden="true"
            >
              {isCustomer ? (
                <span>{supportInitials(event.author)}</span>
              ) : (
                <Headset className="h-4 w-4" />
              )}
            </div>
            <div
              className={cn(
                "min-w-0 max-w-[85%] space-y-1",
                isCustomer && "text-right",
              )}
            >
              <p className="text-muted-foreground text-xs">
                <span className="text-foreground font-medium">
                  {isCustomer ? "You" : event.author || "Support team"}
                </span>
                {" · "}
                {formatDateTime(event.date)}
              </p>
              <div
                className={cn(
                  "overflow-hidden rounded-xl border px-3 py-2 text-left text-sm",
                  isCustomer
                    ? "bg-primary/5 border-primary/20"
                    : "bg-muted/40",
                )}
              >
                {event.subject ? (
                  <p className="mb-1 text-xs font-medium">{event.subject}</p>
                ) : null}
                <div
                  className="space-y-1 break-words [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:leading-relaxed [&_ul]:list-disc [&_ul]:pl-5"
                  dangerouslySetInnerHTML={{ __html: event.content }}
                />
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
