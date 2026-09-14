/** Form header with back button, title, status badge, and action buttons.
 *  When a workflow is active, transitions appear in an "Actions" dropdown menu. */

import { ArrowLeft, CheckCircle, ChevronDown, Loader2, Save, Send, Undo2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DOCSTATUS_MAP } from "../types";
import type { WorkflowTransition } from "../types";

interface FormHeaderProps {
  isNew: boolean;
  metaConfig: any;
  form: Record<string, any>;
  docId?: string;
  docstatus: number;
  isBusy: boolean;
  isEditing: boolean;
  isSubmittable: boolean;
  savedName: string | null;
  error: string | null;
  isSaving: boolean;
  isSubmitting: boolean;
  isCancelling: boolean;
  hasBeenSaved?: boolean;
  onBack: () => void;
  onReset: () => void;
  onSave: () => void;
  onSubmit: () => void;
  onCancel: () => void;
  onAmend: () => void;
  onDuplicate?: () => void;
  hasWorkflow?: boolean;
  workflowTransitions?: WorkflowTransition[];
  currentWorkflowState?: string | null;
  isTransitioning?: boolean;
  onWorkflowAction?: (action: string) => void;
}

export function FormHeader({
  isNew, metaConfig, form, docId, docstatus, isBusy, isEditing, isSubmittable,
  savedName, error: _error, isSaving, isSubmitting, isCancelling, hasBeenSaved = false,
  onBack, onReset, onSave, onSubmit, onCancel, onAmend, onDuplicate,
  hasWorkflow = false, workflowTransitions = [], currentWorkflowState = null,
  isTransitioning = false, onWorkflowAction,
}: FormHeaderProps) {
  const status = DOCSTATUS_MAP[docstatus] ?? { label: "Unknown", variant: "outline" as const };

  const workflowActionsTrigger = (
    <Button disabled={isBusy || isTransitioning} className="gap-1">
      {isTransitioning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
      Actions
      <ChevronDown className="h-4 w-4" />
    </Button>
  );

  return (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack} className="shrink-0"><ArrowLeft className="h-5 w-5" /></Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">{isNew ? `New ${metaConfig.name}` : form?.title || docId}</h1>
              {!isNew && <Badge variant={status.variant as any}>{status.label}</Badge>}
              {currentWorkflowState && !isNew && (
                <Badge variant="outline" className="ml-1">{currentWorkflowState}</Badge>
              )}
            </div>
            <p className="text-muted-foreground text-sm">{metaConfig.name}{form?.owner && !isNew && ` · Created by ${form.owner}`}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isNew && (
            <Button size="sm" onClick={onSave} disabled={isBusy} className="gap-1">
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save
            </Button>
          )}

          {!isNew && hasWorkflow && (
            <>
              {isEditing && (
                <>
                  <Button variant="outline" size="sm" onClick={onReset} disabled={isBusy} className="gap-1">
                    <Undo2 className="h-4 w-4" />Reset
                  </Button>
                  <Button size="sm" onClick={onSave} disabled={isBusy} className="gap-1">
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save
                  </Button>
                </>
              )}
              {!isEditing && workflowTransitions.length > 0 && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    {workflowActionsTrigger}
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="min-w-[180px]">
                    {workflowTransitions.map((t) => (
                      <DropdownMenuItem
                        key={t.name}
                        onClick={() => onWorkflowAction?.(t.action)}
                        disabled={isBusy || isTransitioning}
                        className={
                          t.action.toLowerCase().includes("cancel") || t.action.toLowerCase().includes("reject")
                            ? "text-destructive focus:text-destructive"
                            : ""
                        }
                      >
                        {t.action}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </>
          )}

          {!isNew && !hasWorkflow && (
            <>
              {docstatus === 0 && isEditing && (
                <>
                  <Button variant="outline" size="sm" onClick={onReset} disabled={isBusy} className="gap-1">
                    <Undo2 className="h-4 w-4" />Reset
                  </Button>
                  <Button size="sm" onClick={onSave} disabled={isBusy} className="gap-1">
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save
                  </Button>
                </>
              )}
              {docstatus === 0 && !isEditing && isSubmittable && hasBeenSaved && (
                <Button size="sm" onClick={onSubmit} disabled={isBusy} className="gap-1">
                  {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Submit
                </Button>
              )}
              {isSubmittable && docstatus === 1 && (
                <Button variant="destructive" size="sm" onClick={onCancel} disabled={isBusy} className="gap-1">
                  {isCancelling ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                  Cancel
                </Button>
              )}
              {docstatus === 2 && (
                <Button variant="outline" size="sm" onClick={onAmend} disabled={isBusy} className="gap-1">
                  <Undo2 className="h-4 w-4" />Amend
                </Button>
              )}
            </>
          )}

          {!isNew && !hasWorkflow && docstatus === 0 && onDuplicate && (
            <Button variant="outline" size="sm" onClick={onDuplicate} disabled={isBusy} className="gap-1">
              Duplicate
            </Button>
          )}
        </div>
      </div>

      {savedName && <div className="p-3 bg-green-50 border border-green-200 text-green-700 rounded-md text-sm flex items-center gap-2"><CheckCircle className="h-4 w-4" />Saved as {savedName}</div>}
    </>
  );
}