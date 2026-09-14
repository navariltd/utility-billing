"use client";

import { useFrappePostCall } from "frappe-react-sdk";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

interface ShareModalProps {
  doctype: string;
  name: string;
  data: any[];
  onClose: () => void;
  onSuccess: () => void;
}

const PERMISSION_KEYS = ["read", "write", "submit", "share", "impersonate"];

export function ShareModal({ doctype, name, data = [], onClose, onSuccess }: ShareModalProps) {
  const [userEmail, setUserEmail] = useState("");
  const [newPerms, setNewPerms] = useState({
    read: false,
    write: false,
    submit: false,
    share: false,
    impersonate: false,
  });

  const { call: addShareCall } = useFrappePostCall("frappe.share.add");
  const { call: setPermCall } = useFrappePostCall("frappe.share.set_permission");

  const handleToggleNewPerm = (key: string) => {
    setNewPerms((prev) => ({ ...prev, [key]: !(prev as any)[key] }));
  };

  const handleToggleExistingPerm = async (row: any, key: string, isEveryone = false) => {
    const currentValue = isEveryone ? row[`everyone_${key}`] : row[key];
    try {
      await setPermCall({
        doctype,
        name,
        user: isEveryone ? null : row.user,
        permission_to: key,
        value: currentValue ? 0 : 1,
        everyone: isEveryone ? 1 : 0,
      });
      onSuccess();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userEmail) return;
    try {
      await addShareCall({
        doctype,
        name,
        user: userEmail,
        notify: 1,
        read: newPerms.read ? 1 : 0,
        write: newPerms.write ? 1 : 0,
        submit: newPerms.submit ? 1 : 0,
        share: newPerms.share ? 1 : 0,
        impersonate: newPerms.impersonate ? 1 : 0,
      });
      setUserEmail("");
      setNewPerms({ read: false, write: false, submit: false, share: false, impersonate: false });
      onSuccess();
    } catch (err) {
      console.error(err);
    }
  };

  const everyoneRow = data.find((row: any) => row.everyone === 1) || {
    everyone: 1, read: 0, write: 0, submit: 0, share: 0, impersonate: 0,
  };

  const filteredShares = data.filter((row: any) => {
    if (row.everyone === 1) return false;
    if (!row.user) return false;
    if (row.user === "Administrator") return false;
    return true;
  });

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Share {name}</DialogTitle>
          <DialogDescription>Manage sharing permissions for this document.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-sm">
          {/* Permission grid header */}
          <div className="grid grid-cols-[2.5fr_repeat(5,1fr)] gap-2 items-center pb-2 border-b font-bold text-muted-foreground uppercase tracking-wider text-[10px]">
            <div>User</div>
            <div className="text-center">Read</div>
            <div className="text-center">Write</div>
            <div className="text-center">Submit</div>
            <div className="text-center">Share</div>
            <div className="text-center">Impersonate</div>
          </div>

          {/* Everyone row */}
          <div className="grid grid-cols-[2.5fr_repeat(5,1fr)] gap-2 items-center py-1.5">
            <div className="font-semibold">Everyone</div>
            {PERMISSION_KEYS.map((key) => (
              <div key={key} className="flex justify-center">
                <input
                  type="checkbox"
                  checked={!!(everyoneRow as any)[key]}
                  onChange={() => handleToggleExistingPerm(everyoneRow, key, true)}
                  className="rounded border-input w-4 h-4 accent-primary cursor-pointer"
                />
              </div>
            ))}
          </div>

          {/* Existing shares */}
          {filteredShares.map((row: any) => (
            <div
              key={row.name}
              className="grid grid-cols-[2.5fr_repeat(5,1fr)] gap-2 items-center py-1.5 border-t"
            >
              <div className="truncate text-muted-foreground font-medium" title={row.user}>
                {row.user}
              </div>
              {PERMISSION_KEYS.map((key) => (
                <div key={key} className="flex justify-center">
                  <input
                    type="checkbox"
                    checked={!!row[key]}
                    onChange={() => handleToggleExistingPerm(row, key)}
                    className="rounded border-input w-4 h-4 accent-primary cursor-pointer"
                  />
                </div>
              ))}
            </div>
          ))}

          <hr className="my-2" />

          {/* Add new share */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-[2.5fr_repeat(5,1fr)] gap-2 items-start">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Share with user
                </Label>
                <Input
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder="User email..."
                  className="text-xs"
                />
              </div>
              {PERMISSION_KEYS.map((key) => (
                <div key={key} className="flex flex-col items-center pt-5">
                  <input
                    type="checkbox"
                    checked={(newPerms as any)[key]}
                    onChange={() => handleToggleNewPerm(key)}
                    className="rounded border-input w-4 h-4 accent-primary cursor-pointer"
                  />
                </div>
              ))}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={!userEmail}>
                Add
              </Button>
            </DialogFooter>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default ShareModal;