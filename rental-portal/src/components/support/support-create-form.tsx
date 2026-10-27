/** Raise a support ticket against a booking or an active property tenancy. */

"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage } from "@/lib/errors";
import {
  unwrapMethodResponse,
  type FrappeMethodResponse,
} from "@/lib/frappe-response";
import type { SupportIssuePayload } from "@/types/support";
import { useFrappePostCall } from "frappe-react-sdk";
import { ArrowLeft, Loader2, Send } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

const SUBJECT_LIMIT = 140;
const MESSAGE_LIMIT = 5000;

interface SupportCreateFormProps {
  booking?: string;
  property?: string;
  onCancel: () => void;
  onCreated: (payload: SupportIssuePayload) => void;
}

export function SupportCreateForm({
  booking,
  property,
  onCancel,
  onCreated,
}: SupportCreateFormProps) {
  const endpoint = property
    ? "utility_billing.api.portal.support.create_property_support_issue"
    : "utility_billing.api.portal.support.create_support_issue";
  const { call, loading } = useFrappePostCall<
    FrappeMethodResponse<SupportIssuePayload>
  >(endpoint);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (subject.trim().length < 3) {
      setError("Give the request a subject of at least 3 characters.");
      return;
    }
    if (description.trim().length < 10) {
      setError("Describe the issue in at least 10 characters.");
      return;
    }

    try {
      const response = await call({
        ...(property ? { property } : { booking }),
        subject: subject.trim(),
        description: description.trim(),
      });
      onCreated(unwrapMethodResponse(response));
    } catch (caught) {
      setError(errorMessage(caught, "Your support request could not be created."));
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="space-y-1">
        <h3 className="text-base font-semibold">Raise a support request</h3>
        <p className="text-muted-foreground text-sm">
          Tell us what you need help with. We link the request to this unit so
          the team has the full context.
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="support-subject">Subject</Label>
        <Input
          id="support-subject"
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          placeholder="e.g. Kitchen tap is leaking"
          maxLength={SUBJECT_LIMIT}
          required
        />
        <p className="text-muted-foreground text-right text-xs">
          {subject.length}/{SUBJECT_LIMIT}
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="support-description">What do you need help with?</Label>
        <Textarea
          id="support-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Describe the issue, when it started and anything the team should know."
          rows={7}
          maxLength={MESSAGE_LIMIT}
          required
        />
        <p className="text-muted-foreground text-right text-xs">
          {description.length}/{MESSAGE_LIMIT}
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-4">
        <Button
          type="button"
          variant="ghost"
          className="cursor-pointer"
          onClick={onCancel}
          disabled={loading}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to requests
        </Button>
        <Button type="submit" className="cursor-pointer" disabled={loading}>
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Send className="mr-2 h-4 w-4" />
          )}
          Submit request
        </Button>
      </div>
    </form>
  );
}
