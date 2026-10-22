/** Hook managing save, submit, cancel, duplicate, amend, and workflow actions for DocTypeForm. */

import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useFrappePostCall } from "frappe-react-sdk";
import { toast } from "sonner";
import { parseFrappeError } from "./parse-error";

interface UseFormActionsOptions {
  doctype: string;
  docId?: string;
  form: Record<string, any>;
  isNew: boolean;
  onSuccess?: (name: string) => void;
  onError?: (msg: string) => void;
  onWorkflowSuccess?: () => void;
  /** Called only after a successful submit (docstatus 0 → 1). */
  onSubmitSuccess?: (name: string) => void;
}

interface UseFormActionsReturn {
  isSaving: boolean;
  isSubmitting: boolean;
  isCancelling: boolean;
  isTransitioning: boolean;
  handleSave: () => Promise<void>;
  handleSubmit: () => Promise<void>;
  handleCancel: () => Promise<void>;
  handleDuplicate: () => void;
  handleAmend: () => void;
  handleWorkflowAction: (action: string) => Promise<void>;
}

export function useFormActions(opts: UseFormActionsOptions): UseFormActionsReturn {
  const { doctype, docId, form, isNew, onSuccess, onError, onWorkflowSuccess, onSubmitSuccess } = opts;
  const navigate = useNavigate();
  const { call: updateDoc } = useFrappePostCall("frappe.client.save");
  const { call: saveDocs } = useFrappePostCall("frappe.desk.form.save.savedocs");
  const { call: applyWorkflow } = useFrappePostCall("frappe.model.workflow.apply_workflow");

  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleSave = useCallback(async () => {
    if (!doctype) return;
    setIsSaving(true);
    try {
      const cleaned = { ...form };
      if (isNew) {
        delete cleaned.name;
        delete cleaned.creation;
        delete cleaned.modified;
        delete cleaned.modified_by;
        delete cleaned.owner;
        delete cleaned.docstatus;
        delete cleaned.idx;
      }
      const res: any = await updateDoc({ doc: { doctype, name: !isNew ? docId : undefined, ...cleaned } });
      const saved = res?.message ?? res?.docs?.[0] ?? res;
      if (saved?.name) {
        toast.success(`${doctype} saved successfully${isNew ? ` as ${saved.name}` : ""}`);
        if (isNew) navigate(`/app/${doctype.toLowerCase().replace(/ /g, "-")}/${saved.name}`, { replace: true });
        onSuccess?.(saved.name);
      }
      return saved;
    } catch (err: any) {
      const msg = parseFrappeError(err);
      onError?.(msg);
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  }, [doctype, docId, form, isNew, navigate, onSuccess, onError, updateDoc]);

  const handleSubmit = useCallback(async () => {
    if (!doctype || !docId) return;
    setIsSubmitting(true);
    try {
      const res: any = await saveDocs({ doc: JSON.stringify({ ...form, doctype, name: docId, docstatus: 1 }), action: "Submit" });
      const d = res?.docs?.[0] ?? res?.message?.docs?.[0];
      if (d) {
        toast.success(`${doctype} submitted successfully`);
        onSuccess?.(docId);
        onSubmitSuccess?.(docId);
      }
    } catch (err: any) {
      const msg = parseFrappeError(err);
      onError?.(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  }, [doctype, docId, form, onSuccess, onError, onSubmitSuccess, saveDocs]);

  const handleCancel = useCallback(async () => {
    if (!doctype || !docId) return;
    setIsCancelling(true);
    try {
      const res: any = await saveDocs({ doctype, name: docId, action: "Cancel" });
      if (res?.docs?.[0]) {
        toast.success(`${doctype} cancelled successfully`);
        onSuccess?.(docId);
      }
    } catch (err: any) {
      const msg = parseFrappeError(err);
      onError?.(msg);
      toast.error(msg);
    } finally {
      setIsCancelling(false);
    }
  }, [doctype, docId, onSuccess, onError, saveDocs]);

  const handleDuplicate = useCallback(() => {
    const a: Record<string, any> = { ...form };
    delete a.name;
    delete a.creation;
    delete a.modified;
    delete a.modified_by;
    delete a.owner;
    delete a.docstatus;
    delete a.idx;
    delete a.amended_from;
    navigate(`/app/${doctype.toLowerCase().replace(/ /g, "-")}/new`, { state: { routeOptions: a } });
  }, [form, doctype, navigate]);

  const handleAmend = useCallback(() => {
    const a: Record<string, any> = { ...form, amended_from: docId };
    delete a.name;
    delete a.creation;
    delete a.modified;
    delete a.modified_by;
    delete a.owner;
    delete a.docstatus;
    delete a.idx;
    navigate(`/app/${doctype.toLowerCase().replace(/ /g, "-")}/new`, { state: { routeOptions: a } });
  }, [form, doctype, docId, navigate]);

  const handleWorkflowAction = useCallback(async (action: string) => {
    if (!doctype || !docId) return;
    setIsTransitioning(true);
    try {
      const res: any = await applyWorkflow({
        doc: { ...form, doctype, name: docId },
        action,
      });
      if (res?.message) {
        toast.success(`${action} successful`);
        onWorkflowSuccess?.();
      }
    } catch (err: any) {
      const msg = parseFrappeError(err);
      onError?.(msg);
      toast.error(msg);
    } finally {
      setIsTransitioning(false);
    }
  }, [doctype, docId, form, onError, onWorkflowSuccess, applyWorkflow]);

  return {
    isSaving, isSubmitting, isCancelling, isTransitioning,
    handleSave, handleSubmit, handleCancel, handleDuplicate, handleAmend,
    handleWorkflowAction,
  };
}