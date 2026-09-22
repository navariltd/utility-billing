/** Hook managing workflow detection, transition fetching, and post-action refresh for DocTypeForm. */

import { useCallback, useEffect, useState } from "react";
import { useFrappePostCall } from "frappe-react-sdk";
import type { WorkflowTransition } from "../types";

interface UseWorkflowOptions {
  doctype: string;
  docId?: string;
  form: Record<string, any>;
  isNew: boolean;
  meta?: any;
}

interface UseWorkflowReturn {
  hasWorkflow: boolean;
  workflowTransitions: WorkflowTransition[];
  currentWorkflowState: string | null;
  handleWorkflowSuccess: () => Promise<void>;
}

export function useWorkflow({
  doctype,
  docId,
  form,
  isNew,
  meta,
}: UseWorkflowOptions): UseWorkflowReturn {
  const [hasWorkflow, setHasWorkflow] = useState(false);
  const [workflowTransitions, setWorkflowTransitions] = useState<WorkflowTransition[]>([]);
  const [currentWorkflowState, _setCurrentWorkflowState] = useState<string | null>(null);

  const { call: getTransitions } = useFrappePostCall("frappe.model.workflow.get_transitions");

  useEffect(() => {
    if (!meta) return;
    const wfDocs = meta?.__workflow_docs ?? [];
    if (wfDocs.length > 0) {
      const workflowDefs = wfDocs.filter(
        (d: any) => d.doctype === "Workflow" || (d.workflow_name && d.document_type),
      );
      if (workflowDefs.length > 0) {
        setHasWorkflow(true);
      }
    }
  }, [meta]);

  useEffect(() => {
    if (!isNew && docId && doctype && hasWorkflow) {
      getTransitions({ doctype, name: docId, doc: form })
        .then((res: any) => {
          setWorkflowTransitions(res?.message ?? []);
        })
        .catch(() => {
          setWorkflowTransitions([]);
        });
    }
  }, [isNew, docId, doctype, form, hasWorkflow, getTransitions]);

  const handleWorkflowSuccess = useCallback(async () => {
    if (hasWorkflow && doctype && docId) {
      try {
        const res: any = await getTransitions({ doctype, name: docId, doc: form });
        setWorkflowTransitions(res?.message ?? []);
      } catch {
        setWorkflowTransitions([]);
      }
    }
  }, [hasWorkflow, doctype, docId, form, getTransitions]);

  return {
    hasWorkflow,
    workflowTransitions,
    currentWorkflowState,
    handleWorkflowSuccess,
  };
}