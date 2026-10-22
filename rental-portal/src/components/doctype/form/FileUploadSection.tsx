/**
 * FileUploadSection – manages file attachments for a document with upload, download, and delete.
 */

"use client";

import { useRef, useState } from "react";
import { useFrappeFileUpload, useFrappePostCall } from "frappe-react-sdk";
import { AlertTriangle, Paperclip, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FileUploadSectionProps {
  currentDoctype: string;
  currentName: string;
  attachments: any[];
  setAttachments: (a: any[]) => void;
  reloadData?: () => void;
}

export function FileUploadSection({
  currentDoctype,
  currentName,
  attachments,
  setAttachments,
  reloadData,
}: FileUploadSectionProps) {
  const { upload } = useFrappeFileUpload();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileToDelete, setFileToDelete] = useState<any>(null);
  const { call: removeAttachmentCall } = useFrappePostCall(
    "frappe.desk.form.utils.remove_attach",
  );

  const handleTriggerUpload = () => fileInputRef.current?.click();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await upload(file, {
        isPrivate: 0,
        folder: "Home/Attachments",
        doctype: currentDoctype,
        docname: currentName,
      } as any);
      reloadData?.();
    } catch (err) {
      console.error(err);
    }
  };

  const handleConfirmDelete = async () => {
    if (!fileToDelete) return;
    try {
      await removeAttachmentCall({
        fid: fileToDelete.name,
        dt: currentDoctype,
        dn: currentName,
      });
      setAttachments(
        attachments.filter((item) => item.name !== fileToDelete.name),
      );
      reloadData?.();
    } catch (err) {
      console.error(err);
    } finally {
      setFileToDelete(null);
    }
  };

  return (
    <div className="border border-border/60 p-3 rounded-lg space-y-3 bg-card relative">
      <div className="flex items-center justify-between text-muted-foreground py-0.5">
        <span className="flex items-center gap-2 font-bold uppercase tracking-wider text-[10px] text-muted-foreground">
          <Paperclip className="w-3.5 h-3.5" /> Attachments
        </span>
        <button
          onClick={handleTriggerUpload}
          className="w-5 h-5 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-primary transition-all duration-300 border border-border/40 shadow-sm bg-card"
        >
          <Plus className="w-3 h-3" />
        </button>
      </div>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
      />
      <div className="space-y-2">
        {attachments.map((file: any, index: number) => (
          <div
            key={file.name || index}
            className="flex items-center justify-between group/file py-1 px-2 rounded-lg bg-card border border-border/40 hover:border-primary/30 transition-colors"
          >
            <a
              href={file.file_url}
              target="_blank"
              rel="noreferrer"
              className="text-foreground font-semibold hover:text-primary truncate max-w-[85%] transition-colors text-xs"
            >
              {file.file_name}
            </a>
            <button
              onClick={() => setFileToDelete(file)}
              className="text-muted-foreground hover:text-destructive opacity-0 group-hover/file:opacity-100 transition-opacity p-0.5"
            >
              <X className="w-2.5 h-2.5" />
            </button>
          </div>
        ))}
        {attachments.length === 0 && (
          <p className="text-muted-foreground text-[11px] italic px-1">
            No files attached
          </p>
        )}
      </div>
      {fileToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-card rounded-lg border shadow-lg p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-destructive/10 flex items-center justify-center text-destructive shrink-0 border border-destructive/20">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <h3 className="text-foreground font-bold text-sm">
                  Delete Attachment
                </h3>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  Are you sure you want to remove{" "}
                  <span className="font-semibold text-foreground break-all">
                    {fileToDelete.file_name}
                  </span>
                  ? This action cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFileToDelete(null)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleConfirmDelete}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default FileUploadSection;