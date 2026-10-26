/** Reply composer for a support ticket. */

"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage } from "@/lib/errors";
import {
  unwrapMethodResponse,
  type FrappeMethodResponse,
} from "@/lib/frappe-response";
import type { SupportTimelineEvent } from "@/types/support";
import { useFrappePostCall } from "frappe-react-sdk";
import { Loader2, Send } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

const MESSAGE_LIMIT = 5000;

interface SupportReplyFormProps {
  issue: string;
  isResolved: boolean;
  onReplied: (timeline: SupportTimelineEvent[]) => void;
}

export function SupportReplyForm({
  issue,
  isResolved,
  onReplied,
}: SupportReplyFormProps) {
  const { call, loading } = useFrappePostCall<
    FrappeMethodResponse<{
      comment: string;
      timeline: SupportTimelineEvent[];
    }>
  >("utility_billing.api.portal.support.reply_to_support_issue");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    if (!message.trim()) {
      setError("Write a reply before sending it.");
      return;
    }

    try {
      const response = await call({ issue, message: message.trim() });
      const payload = unwrapMethodResponse(response);
      setMessage("");
      toast.success("Reply sent to the support team.");
      onReplied(payload.timeline);
    } catch (caught) {
      setError(errorMessage(caught, "Your reply could not be sent."));
    }
  };

  return (
    <div className="bg-muted/20 space-y-3 rounded-xl border p-4">
      <div className="space-y-1">
        <p className="text-sm font-medium">Reply</p>
        <p className="text-muted-foreground text-xs">
          {isResolved
            ? "This request is marked resolved. Reply if you still need help."
            : "Add more detail or answer the support team's questions."}
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Textarea
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.preventDefault();
            void submit();
          }
        }}
        placeholder="Write your reply…"
        rows={4}
        maxLength={MESSAGE_LIMIT}
        aria-label="Reply to the support team"
      />

      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-muted-foreground text-xs">
          {message.length}/{MESSAGE_LIMIT} · Ctrl/⌘ + Enter to send
        </span>
        <Button
          type="button"
          size="sm"
          className="cursor-pointer"
          onClick={submit}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Send className="mr-2 h-4 w-4" />
          )}
          Send reply
        </Button>
      </div>
    </div>
  );
}
