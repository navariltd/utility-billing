/**
 * DocumentSidebar – collapsible right sidebar with image, assignments, file upload,
 * tags, shares, and created/modified info.
 */

"use client";

import { useEffect, useState } from "react";
import { useFrappePostCall } from "frappe-react-sdk";
import { ArrowLeftRight, Calendar, Edit3, Heart, Paperclip, Plus, Printer, Share2, Tags, User } from "lucide-react";
import { timeAgo } from "../utils";
import { FileUploadSection } from "./FileUploadSection";
import { TagSection } from "./TagSection";
import { AssignmentModal } from "./AssignmentModal";
import { ShareModal } from "./ShareModal";

interface DocumentSidebarProps {
  form: Record<string, any>;
  docData?: any;
  metaConfig?: any;
  reloadData: () => void;
}

export function DocumentSidebar({
  form,
  docData,
  metaConfig,
  reloadData,
}: DocumentSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [attachments, setAttachments] = useState<any[]>([]);
  const [assignments, setAssignments] = useState<any[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [shares, setShares] = useState<any[]>([]);
  const [metaInfo, setMetaInfo] = useState<any>(null);
  const [isAssignOpen, setIsAssignOpen] = useState(false);
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  const [_isRenameOpen, setIsRenameOpen] = useState(false);
  const { call: toggleLikeCall } = useFrappePostCall(
    "frappe.desk.like.toggle_like",
  );

  const docinfo = docData?.docinfo || {};
  const currentDoctype: string = form.doctype || "";
  const currentName: string = form.name || "";
  const currentTitle = form.title || form.name;

  const imageField = metaConfig?.image_field;
  const imageUrl = imageField ? form[imageField] : null;

  useEffect(() => {
    if (!docData) return;
    const dinfo = docData.docinfo || {};
    const mainDoc = form;

    if (mainDoc.creation || mainDoc.modified) {
      setMetaInfo({
        creation: mainDoc.creation,
        owner: mainDoc.owner,
        modified: mainDoc.modified,
        modified_by: mainDoc.modified_by,
      });
    }
    if (dinfo?.attachments) setAttachments(dinfo.attachments);
    if (dinfo?.assignments) setAssignments(dinfo.assignments);
    if (dinfo?.shared) setShares(dinfo.shared);
    if (mainDoc._user_tags) {
      setTags(String(mainDoc._user_tags).split(",").filter(Boolean));
    } else if (dinfo?.tags) {
      setTags(
        typeof dinfo.tags === "string"
          ? dinfo.tags.split(",").filter(Boolean)
          : dinfo.tags,
      );
    }
    if (dinfo?.like_logs) {
      setIsLiked(dinfo.like_logs.some((l: any) => l.owner === "Administrator"));
    }
  }, [docData, form]);

  const handleLikeToggle = async () => {
    try {
      await toggleLikeCall({
        doctype: currentDoctype,
        name: currentName,
        add: !isLiked ? "Yes" : "No",
      });
      setIsLiked(!isLiked);
    } catch (err) {
      console.error(err);
    }
  };

  if (!currentDoctype || !currentName) return null;

  if (isCollapsed) {
    return (
      <div className="w-12 flex-shrink-0 flex flex-col h-full border-l bg-card items-center py-4 relative select-none group">
        <button
          onClick={() => setIsCollapsed(false)}
          className="absolute -left-3 top-1/2 -translate-y-1/2 z-20 flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md ring-2 ring-background opacity-0 group-hover:opacity-100 transition-all duration-300 hover:scale-110"
        >
          <ArrowLeftRight className="w-3 h-3 rotate-180" />
        </button>
        <div className="flex flex-col gap-6 mt-12 text-muted-foreground">
          <User className="w-4 h-4 hover:text-primary transition-colors" />
          <Paperclip className="w-4 h-4 hover:text-primary transition-colors" />
          <Tags className="w-4 h-4 hover:text-primary transition-colors" />
          <Share2 className="w-4 h-4 hover:text-primary transition-colors" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full lg:w-80 flex-shrink-0 flex flex-col border-l bg-card relative overflow-visible select-none group">
      <button
        onClick={() => setIsCollapsed(true)}
        className="absolute -left-3 top-1/2 -translate-y-1/2 z-20 flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md ring-2 ring-background opacity-0 group-hover:opacity-100 transition-all duration-300 hover:scale-110"
      >
        <ArrowLeftRight className="w-3 h-3" />
      </button>

      {/* Document Header - title, rename, like */}
      <div className="bg-card p-4 border-b flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-bold text-foreground leading-tight truncate">
            {currentTitle !== currentName ? currentTitle : currentName}
          </h2>
          {currentTitle !== currentName && (
            <p className="text-xs text-muted-foreground font-medium mt-0.5 truncate">
              {currentName}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 text-muted-foreground shrink-0 ml-2">
          {metaConfig?.allow_rename === 1 && (
            <button
              onClick={() => setIsRenameOpen(true)}
              className="hover:text-primary transition-colors p-1"
            >
              <Edit3 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={() => window.open(`/print?doctype=${encodeURIComponent(currentDoctype)}&name=${encodeURIComponent(currentName)}`, "_blank")}
            className="hover:text-primary transition-colors p-1"
            title="Print"
          >
            <Printer className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleLikeToggle}
            className={`transition-colors p-1 ${isLiked ? "text-red-500 hover:text-red-600" : "text-muted-foreground hover:text-red-500 opacity-60 hover:opacity-100"}`}
            title={isLiked ? "Unlike" : "Like"}
          >
            {isLiked ? (
              <Heart className="w-3.5 h-3.5 fill-current" />
            ) : (
              <Heart className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 text-xs">
        {/* Image field */}
        {imageUrl && (
          <div className="bg-card rounded-lg border overflow-hidden">
            <div className="p-4 flex justify-center items-center min-h-[150px]">
              <img
                src={imageUrl}
                alt="Document"
                className="max-w-full max-h-48 object-contain rounded-lg border"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            </div>
          </div>
        )}

        {/* Assignments */}
        <div className="border border-border/60 p-3 rounded-lg space-y-3 bg-card">
          <div className="flex items-center justify-between text-muted-foreground py-0.5">
            <span className="flex items-center gap-2 font-bold uppercase tracking-wider text-[10px] text-muted-foreground">
              <User className="w-3.5 h-3.5" /> Assign
            </span>
            <button
              onClick={() => setIsAssignOpen(true)}
              className="w-5 h-5 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-primary transition-all duration-300 border border-border/40 shadow-sm bg-card"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-2">
            {assignments.map((assign: any, index: number) => {
              const displayName =
                docinfo?.user_info?.[assign.owner]?.fullname ||
                assign.owner ||
                "Unknown User";
              return (
                <div
                  key={assign.name || index}
                  className="flex items-center gap-2.5 py-1 px-2 rounded-lg bg-card border border-border/40 shadow-sm"
                >
                  <div className="w-6 h-6 shrink-0 rounded-full bg-muted text-muted-foreground flex items-center justify-center font-bold text-[10px]">
                    {displayName.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-foreground font-semibold truncate text-xs">
                    {displayName}
                  </span>
                </div>
              );
            })}
            {assignments.length === 0 && (
              <p className="text-muted-foreground text-[11px] italic px-1">
                No active assignments
              </p>
            )}
          </div>
        </div>

        {/* File upload */}
        <FileUploadSection
          currentDoctype={currentDoctype}
          currentName={currentName}
          attachments={attachments}
          setAttachments={setAttachments}
          reloadData={reloadData}
        />

        {/* Tags */}
        <div className="border border-border/60 p-3 rounded-lg bg-card">
          <TagSection
            currentDoctype={currentDoctype}
            currentName={currentName}
            initialTags={tags}
            reloadData={reloadData}
          />
        </div>

        {/* Share */}
        <div className="border border-border/60 p-3 rounded-lg space-y-3 bg-card">
          <div className="flex items-center justify-between text-muted-foreground py-0.5">
            <span className="flex items-center gap-2 font-bold uppercase tracking-wider text-[10px] text-muted-foreground">
              <Share2 className="w-3.5 h-3.5" /> Share
            </span>
            <button
              onClick={() => setIsShareOpen(true)}
              className="w-5 h-5 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-primary transition-all duration-300 border border-border/40 shadow-sm bg-card"
            >
              <Plus className="w-3 h-3" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {shares.map((share: any, index: number) => {
              const shareUser = share.everyone
                ? "Everyone"
                : docinfo?.user_info?.[share.user]?.fullname ||
                  share.user ||
                  "Unknown User";
              return (
                <div
                  key={share.name || index}
                  title={shareUser}
                  className="w-7 h-7 rounded-full bg-muted border border-border text-muted-foreground flex items-center justify-center font-bold text-[10px] shadow-sm hover:scale-105 transition-transform"
                >
                  {shareUser.charAt(0).toUpperCase()}
                </div>
              );
            })}
            {shares.length === 0 && (
              <p className="text-muted-foreground text-[11px] italic px-1">
                Not shared with anyone
              </p>
            )}
          </div>
        </div>

        {/* Created by / Modified by */}
        {metaInfo && (
          <div className="bg-muted/30 rounded-lg p-3 border border-border/40">
            <div className="space-y-3 text-xs">
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-card border border-border flex items-center justify-center text-muted-foreground flex-shrink-0 shadow-sm">
                  <Calendar className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                    Created By
                  </p>
                  <p className="text-foreground font-semibold truncate mt-0.5">
                    {docinfo?.user_info?.[metaInfo.owner]?.fullname ||
                      metaInfo.owner}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5 font-medium">
                    {timeAgo(metaInfo.creation)}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 border-t border-border/60 pt-3">
                <div className="w-7 h-7 rounded-lg bg-card border border-border flex items-center justify-center text-muted-foreground flex-shrink-0 shadow-sm">
                  <Edit3 className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                    Last Modified By
                  </p>
                  <p className="text-foreground font-semibold truncate mt-0.5">
                    {docinfo?.user_info?.[metaInfo.modified_by]?.fullname ||
                      metaInfo.modified_by}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5 font-medium">
                    {timeAgo(metaInfo.modified)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Assignment Modal */}
      {isAssignOpen && (
        <AssignmentModal
          doctype={currentDoctype}
          name={currentName}
          onClose={() => setIsAssignOpen(false)}
          onSuccess={() => {
            setIsAssignOpen(false);
            reloadData();
          }}
        />
      )}

      {/* Share Modal */}
      {isShareOpen && (
        <ShareModal
          doctype={currentDoctype}
          name={currentName}
          data={shares}
          onClose={() => setIsShareOpen(false)}
          onSuccess={() => {
            setIsShareOpen(false);
            reloadData();
          }}
        />
      )}
    </div>
  );
}

export default DocumentSidebar;
