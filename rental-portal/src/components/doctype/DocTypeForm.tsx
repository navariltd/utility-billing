/** Full document form for any Frappe doctype with save/submit/cancel, tabbed layout, and workflow support. */

"use client";

import { useFrappeGetCall } from "frappe-react-sdk";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { Skeleton } from "@/components/ui/skeleton";
import { useUser } from "@/contexts/user-context";
import { ConfirmCancelDialog, ConfirmSubmitDialog, ErrorDialog } from "./form/ConfirmationDialogs";
import { FormHeader } from "./form/FormHeader";
import { TabbedForm } from "./form/TabbedForm";
import { useFormActions } from "./form/form-actions";
import { useWorkflow } from "./form/useWorkflow";
import { isPermissionError, parseFrappeError } from "./form/parse-error";
import type { FrappeFieldMeta } from "./types";

interface DocTypeFormProps {
  doctype: string;
  docname?: string;
  forceNew?: boolean;
  onSuccess?: (name: string) => void;
  onBack?: () => void;
}

type ConfirmAction = "submit" | "cancel" | null;

export function DocTypeForm({ doctype, docname: propDocname, forceNew = false, onSuccess, onBack }: DocTypeFormProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { id: routeId } = useParams();
  const [searchParams] = useSearchParams();
  const { isLoading: userLoading } = useUser();

  const isNew = forceNew || routeId === "new";
  const docId = propDocname || routeId;

  const [schemaFields, setSchemaFields] = useState<FrappeFieldMeta[]>([]);
  const [metaConfig, setMetaConfig] = useState<any>(null);
  const [form, setForm] = useState<Record<string, any>>({});
  const [originalDoc, setOriginalDoc] = useState<any>(null);
  const [docstatus, setDocstatus] = useState(0);
  const [isSubmittable, setIsSubmittable] = useState(false);
  const [isLoadingDoc, setIsLoadingDoc] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [metaReady, setMetaReady] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});
  const [hasBeenSaved, setHasBeenSaved] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  const { data: schemaData, error: schemaError } = useFrappeGetCall(
    "frappe.desk.form.load.getdoctype", { doctype, with_parent: 1 },
    doctype ? `dtf-meta-${doctype}` : null,
  );

  const { data: docData, error: docError, mutate: reloadDoc } = useFrappeGetCall(
    "frappe.desk.form.load.getdoc", { doctype, name: docId },
    doctype && docId && !isNew ? `dtf-doc-${doctype}-${docId}` : null,
  );

  const { hasWorkflow, workflowTransitions, currentWorkflowState, handleWorkflowSuccess } = useWorkflow({
    doctype, docId, form, isNew, meta: metaConfig,
  });

  const {
    isSaving, isSubmitting, isCancelling, isTransitioning,
    handleSave, handleSubmit, handleCancel, handleDuplicate, handleAmend,
    handleWorkflowAction,
  } = useFormActions({
    doctype, docId, form, isNew,
    onSuccess: (name) => {
      // Reload the doc after save/submit/cancel so docstatus-driven actions
      // (Submit/Cancel/Amend) reflect the latest server state without a reload.
      reloadDoc();
      onSuccess?.(name);
    },
    onError: (msg) => { setError(msg); setErrorDialogOpen(true); },
    onWorkflowSuccess: async () => {
      await handleWorkflowSuccess();
      await reloadDoc();
    },
  });

  const routeOptions = useMemo(() => {
    const opts: Record<string, string> = {};
    const stateRouteOptions = (location.state as any)?.routeOptions;
    if (stateRouteOptions && typeof stateRouteOptions === "object") {
      for (const [key, value] of Object.entries(stateRouteOptions)) {
        opts[key] = String(value ?? "");
      }
    }
    for (const [key, value] of searchParams.entries()) {
      opts[key] = value;
    }
    return opts;
  }, [location.state, searchParams]);

  useEffect(() => {
    if (schemaError) {
      const msg = parseFrappeError(schemaError);
      setError(msg);
      toast.error(msg);
      return;
    }
    if (schemaData?.message?.docs?.length || schemaData?.docs?.length) {
      const docs = schemaData.message?.docs ?? schemaData.docs ?? [];
      const meta = docs.find((d: any) => d.name === doctype) ?? docs[0];
      if (meta) {
        setSchemaFields((meta.fields ?? []).map((f: any) => ({ ...f, required: f.reqd || f.required, read_only: f.read_only })));
        setMetaConfig(meta);
        setIsSubmittable(meta.is_submittable === 1);
      }
      setMetaReady(true);
    }
  }, [schemaData, schemaError, doctype]);

  useEffect(() => {
    if (!isNew || !metaReady || !schemaFields.length || !Object.keys(routeOptions).length) return;
    const prefill: Record<string, any> = {};
    let hasAny = false;
    for (const [key, value] of Object.entries(routeOptions)) {
      const df = schemaFields.find((f: any) => f.fieldname === key);
      if (!df || df.no_copy || key.startsWith("__") || key === "name" || key === "doctype") continue;
      let val: any = value;
      if (typeof val === "string") {
        try { const parsed = JSON.parse(val); if (!Array.isArray(parsed) && typeof parsed === "object" && parsed !== null) val = parsed; } catch {}
      }
      prefill[key] = val;
      hasAny = true;
    }
    if (hasAny) {
      setForm((prev) => ({ ...prev, ...prefill }));
      setOriginalDoc(JSON.parse(JSON.stringify({ ...prefill })));
    }
  }, [isNew, metaReady, schemaFields, routeOptions]);

  useEffect(() => {
    if (isNew && metaReady) {
      if (Object.keys(routeOptions).length === 0) {
        setForm({});
        setOriginalDoc(null);
        setDocstatus(0);
        setIsEditing(true);
        setIsLoadingDoc(false);
      }
      return;
    }
    if (docError) {
      if (isPermissionError(docError)) { navigate("/errors/forbidden", { replace: true }); return; }
      const msg = parseFrappeError(docError);
      setError(msg);
      toast.error(msg);
      setIsLoadingDoc(false);
      return;
    }
    if (docData) {
      const doc = docData?.message?.docs?.[0] ?? docData?.docs?.[0] ?? {};
      if (doc.name) {
        setForm(doc);
        setOriginalDoc(JSON.parse(JSON.stringify(doc)));
        setDocstatus(doc.docstatus ?? 0);
        setIsEditing(false);
        setHasBeenSaved(true);
      }
      setIsLoadingDoc(false);
    }
  }, [docData, docError, isNew, metaReady, routeOptions, navigate]);

  useEffect(() => {
    if (isNew && metaReady && isLoadingDoc) { setIsLoadingDoc(false); setIsEditing(true); }
  }, [isNew, metaReady, isLoadingDoc]);

  useEffect(() => {
    if (isNew) { setIsEditing(true); return; }
    if (originalDoc) {
      const isDirty = JSON.stringify(form) !== JSON.stringify(originalDoc);
      setIsEditing(isDirty);
      if (isDirty && hasBeenSaved) setHasBeenSaved(false);
    }
  }, [form, originalDoc, isNew, hasBeenSaved]);

  useEffect(() => {
    if (!metaReady || !schemaFields.length) return;
    const collapsed: Record<string, boolean> = {};
    schemaFields.forEach((f: any) => {
      if (f.fieldtype === "Section Break" && f.collapsible) collapsed[f.fieldname] = f.collapsed !== 0;
    });
    setCollapsedSections(collapsed);
  }, [metaReady, schemaFields]);

  const toggleSection = (fn: string) => setCollapsedSections((p) => ({ ...p, [fn]: !p[fn] }));
  const handleChange = (value: any, fieldname?: string) => { if (!fieldname) return; setForm((p) => ({ ...p, [fieldname]: value })); };
  const handleBack = () => { if (onBack) onBack(); else navigate(`/app/${doctype.toLowerCase().replace(/ /g, "-")}`); };
  const handleReset = () => { setForm(JSON.parse(JSON.stringify(originalDoc))); setIsEditing(false); setError(null); };

  if (userLoading || !metaReady) {
    return (
      <div className="px-4 lg:px-6 space-y-6 pb-8">
        <Skeleton className="h-10 w-20" />
        <Skeleton className="h-8 w-48" />
        <div className="space-y-4">
          <Skeleton className="h-[200px] w-full rounded-lg" />
          <Skeleton className="h-[300px] w-full rounded-lg" />
        </div>
      </div>
    );
  }
  if (!metaConfig) {
    return <div className="px-4 lg:px-6 text-center py-20 text-muted-foreground">Failed to load configuration.</div>;
  }

  const doctypeLabel = metaConfig?.name || doctype;

  return (
    <div className="px-4 lg:px-6 space-y-6 pb-8">
      <FormHeader
        isNew={isNew}
        metaConfig={metaConfig}
        form={form}
        docId={docId}
        docstatus={docstatus}
        isBusy={isSaving || isSubmitting || isCancelling || isTransitioning}
        isEditing={isEditing}
        isSubmittable={isSubmittable}
        savedName={null}
        error={error}
        isSaving={isSaving}
        isSubmitting={isSubmitting}
        isCancelling={isCancelling}
        hasBeenSaved={hasBeenSaved}
        onBack={handleBack}
        onReset={handleReset}
        onSave={handleSave}
        onSubmit={() => setConfirmAction("submit")}
        onCancel={() => setConfirmAction("cancel")}
        onAmend={handleAmend}
        onDuplicate={docstatus === 0 && !isNew ? handleDuplicate : undefined}
        hasWorkflow={hasWorkflow}
        workflowTransitions={workflowTransitions}
        currentWorkflowState={currentWorkflowState}
        isTransitioning={isTransitioning}
        onWorkflowAction={handleWorkflowAction}
      />

      <TabbedForm
        schemaFields={schemaFields}
        form={form}
        doctype={doctype}
        docData={docData}
        metaConfig={metaConfig}
        isReadOnly={docstatus !== 0}
        isNew={isNew}
        isLoadingDoc={isLoadingDoc}
        onFieldChange={handleChange}
        collapsedSections={collapsedSections}
        onToggleSection={toggleSection}
        reloadData={handleSave as any}
        reloadDoc={reloadDoc}
      />

      <ConfirmSubmitDialog
        open={confirmAction === "submit"}
        onOpenChange={(open) => { if (!open) setConfirmAction(null); }}
        doctypeLabel={doctypeLabel}
        isSubmitting={isSubmitting}
        onConfirm={() => { setConfirmAction(null); handleSubmit(); }}
      />

      <ErrorDialog
        open={errorDialogOpen}
        onOpenChange={setErrorDialogOpen}
        title="Error"
        message={error || ""}
      />

      <ConfirmCancelDialog
        open={confirmAction === "cancel"}
        onOpenChange={(open) => { if (!open) setConfirmAction(null); }}
        doctypeLabel={doctypeLabel}
        isCancelling={isCancelling}
        onConfirm={() => { setConfirmAction(null); handleCancel(); }}
      />
    </div>
  );
}

export default DocTypeForm;