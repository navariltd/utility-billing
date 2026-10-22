"use client";

import { useFrappePostCall } from "frappe-react-sdk";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LinkField } from "@/components/fields/LinkField";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

interface AssignmentModalProps {
  doctype: string;
  name: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function AssignmentModal({ doctype, name, onClose, onSuccess }: AssignmentModalProps) {
  const [assignToMe, setAssignToMe] = useState(false);
  const [assignTo, setAssignTo] = useState("");
  const [completeBy, setCompleteBy] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [description, setDescription] = useState(name || "");

  const { call: assignToCall } = useFrappePostCall("frappe.desk.form.assign_to.add");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignTo && !assignToMe) return;

    try {
      await assignToCall({
        assign_to_me: assignToMe ? 1 : 0,
        assign_to: JSON.stringify(assignToMe ? [] : [assignTo]),
        date: completeBy || null,
        priority,
        description: description || undefined,
        doctype,
        name,
        bulk_assign: false,
        re_assign: false,
      });
      onSuccess();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent
        className="sm:max-w-lg"
        // Prevent Radix UI from stealing focus/intercepting clicks outside the dialog.
        // This allows the LinkField dropdown (portaled to document.body) to receive events.
        onPointerDownOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Assign to</DialogTitle>
          <DialogDescription>Assign this document to a user.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Assign to me */}
          <label className="flex items-center gap-3 p-2.5 rounded-lg border cursor-pointer select-none hover:bg-muted/30 transition-colors">
            <input
              type="checkbox"
              checked={assignToMe}
              onChange={(e) => {
                setAssignToMe(e.target.checked);
                if (e.target.checked) setAssignTo("");
              }}
              className="rounded focus:ring-primary w-4 h-4 accent-primary"
            />
            <span className="text-sm font-medium">Assign to me</span>
          </label>

          {/* Assign to user */}
          <div className={assignToMe ? "opacity-40 pointer-events-none" : ""}>
            <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5 block">
              Assign To
            </Label>
            <div className="border border-input rounded-md p-1 focus-within:ring-1 focus-within:ring-ring">
              <LinkField
                doctype="User"
                value={assignTo}
                onChange={(val: any) => {
                  setAssignTo(val || "");
                  if (val) setAssignToMe(false);
                }}
                placeholder="Search user..."
              />
            </div>
          </div>

          {/* Complete by / Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Complete By
              </Label>
              <Input
                type="date"
                value={completeBy}
                onChange={(e) => setCompleteBy(e.target.value)}
                className="text-xs"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Priority
              </Label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full text-xs p-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring bg-background cursor-pointer"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
              </select>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Comment
            </Label>
            <textarea
              placeholder="Write description/context..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full text-xs p-2.5 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring resize-none h-24 bg-background"
            />
          </div>

          <DialogFooter className="pt-2 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!assignTo && !assignToMe}>
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default AssignmentModal;