/**
 * DocumentActivity – renders activity timeline (comments, likes, versions).
 */

"use client";

import { useFrappeAuth, useFrappePostCall } from "frappe-react-sdk";
import { Heart, History, MessageSquare, SendHorizonal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { timeAgo } from "../utils";

interface DocumentActivityProps {
  form: Record<string, any>;
  docData?: any;
  onReload?: () => void;
}

export function DocumentActivity({ form, docData, onReload }: DocumentActivityProps) {
  const { currentUser } = useFrappeAuth();
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);
  const [showAllActivity, setShowAllActivity] = useState(true);
  const [commentText, setCommentText] = useState("");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const docinfo = docData?.docinfo || form?.docinfo || {};
  const userInfo = docinfo.user_info || {};
  const currentDoctype: string = form.doctype || "";
  const currentName: string = form.name || "";

  const { call: addCommentCall } = useFrappePostCall(
    "frappe.desk.form.utils.add_comment",
  );

  useEffect(() => {
    if (!docinfo) return;
    const compiled: any[] = [];

    if (docinfo.comments) {
      docinfo.comments.forEach((c: any) =>
        compiled.push({ ...c, groupType: "Comment" }),
      );
    }
    if (docinfo.assignment_logs) {
      docinfo.assignment_logs.forEach((a: any) =>
        compiled.push({ ...a, groupType: "Log", logType: "Assignment" }),
      );
    }
    if (docinfo.attachment_logs) {
      docinfo.attachment_logs.forEach((at: any) =>
        compiled.push({ ...at, groupType: "Log", logType: "Attachment" }),
      );
    }
    if (docinfo.like_logs) {
      docinfo.like_logs.forEach((l: any) =>
        compiled.push({ ...l, groupType: "Log", logType: "Like" }),
      );
    }
    if (docinfo.versions) {
      docinfo.versions.forEach((v: any) => {
        try {
          const parsedData = JSON.parse(v.data || "{}");
          if (parsedData.changed && parsedData.changed.length > 0) {
            parsedData.changed.forEach(
              ([field, fromVal, toVal]: [string, any, any]) => {
                const label = field
                  .replace(/_/g, " ")
                  .replace(/\b\w/g, (l: string) => l.toUpperCase());
                compiled.push({
                  name: `${v.name}_${field}`,
                  creation: v.creation,
                  owner: v.owner,
                  groupType: "Log",
                  logType: "Version",
                  content: `changed <span class="font-semibold text-foreground bg-muted px-1.5 py-0.5 rounded text-[11px] mx-1">${label}</span> from <span class="text-destructive bg-destructive/10 px-1 py-0.5 rounded line-through text-[11px]">${fromVal === null ? "null" : fromVal}</span> to <span class="font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded text-[11px]">${toVal}</span>`,
                });
              },
            );
          }
        } catch {}
      });
    }

    compiled.sort(
      (a, b) => new Date(b.creation).getTime() - new Date(a.creation).getTime(),
    );
    setTimelineEvents(compiled);
  }, [docinfo]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [commentText]);

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !commentText.trim() ||
      !currentDoctype ||
      !currentName ||
      isSubmittingComment
    )
      return;
    setIsSubmittingComment(true);
    try {
      const userName = currentUser || "";
      const userEmail = userInfo?.[userName]?.email || "";
      await addCommentCall({
        reference_doctype: currentDoctype,
        reference_name: currentName,
        content: commentText.trim(),
        comment_email: userEmail,
        comment_by: userName,
      });
      setCommentText("");
      // Refetch doc data to reload the activity timeline
      if (onReload) {
        onReload();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const filteredEvents = showAllActivity
    ? timelineEvents
    : timelineEvents.filter((e) => e.groupType === "Comment");
  const totalCommentsCount = timelineEvents.filter(
    (e) => e.groupType === "Comment",
  ).length;

  const getLogStyles = (logType?: string) => {
    switch (logType) {
      case "Like":
        return {
          dotBg: "bg-rose-50 border-rose-200",
          icon: <Heart className="w-[7px] h-[7px] text-rose-500" />,
        };
      case "Assignment":
        return {
          dotBg: "bg-indigo-50 border-indigo-200",
          icon: <History className="w-[7px] h-[7px] text-indigo-500" />,
        };
      case "Attachment":
        return {
          dotBg: "bg-cyan-50 border-cyan-200",
          icon: <History className="w-[7px] h-[7px] text-cyan-500" />,
        };
      case "Version":
        return {
          dotBg: "bg-amber-50 border-amber-200",
          icon: <History className="w-[7px] h-[7px] text-amber-500" />,
        };
      default:
        return {
          dotBg: "bg-slate-50 border-slate-200",
          icon: <div className="w-1.5 h-1.5 rounded-full bg-slate-400" />,
        };
    }
  };

  if (!currentDoctype) return null;

  return (
    <div className="w-full mx-auto mt-4 bg-card rounded-lg border shadow-sm">
      <div className="px-5 py-3 border-b flex items-center justify-between bg-muted/20">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center border border-indigo-100">
            <MessageSquare className="w-3.5 h-3.5 text-indigo-600" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-foreground tracking-tight">
              Activity
            </h4>
            <p className="text-[11px] text-muted-foreground font-medium">
              {totalCommentsCount}{" "}
              {totalCommentsCount === 1 ? "comment" : "comments"} recorded
            </p>
          </div>
        </div>
        <label className="inline-flex items-center cursor-pointer select-none gap-2">
          <span className="text-xs font-semibold text-muted-foreground">
            Filter actions
          </span>
          <input
            type="checkbox"
            checked={showAllActivity}
            onChange={(e) => setShowAllActivity(e.target.checked)}
            className="toggle"
          />
        </label>
      </div>

      <div className="p-4 bg-card border-b flex gap-3.5 items-start">
        <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-indigo-100 shrink-0 bg-muted flex items-center justify-center">
          <div className="w-full h-full flex items-center justify-center text-xs font-black text-indigo-400 bg-indigo-50">
            U
          </div>
        </div>
        <form
          onSubmit={handlePostComment}
          className="flex-1 relative rounded-lg border bg-muted/30 focus-within:bg-card focus-within:border-primary p-1.5 flex items-center"
        >
          <textarea
            ref={textareaRef}
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Write an update, response or comment..."
            rows={1}
            className="flex-1 bg-transparent border-0 pl-2.5 pr-12 py-1.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-0 resize-none min-h-[32px] leading-relaxed"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handlePostComment(e);
              }
            }}
          />
          {commentText.trim() && (
            <button
              type="submit"
              disabled={isSubmittingComment}
              className="absolute right-2 p-2 rounded-lg bg-primary text-primary-foreground hover:opacity-95 shadow-sm transition-all duration-150 flex items-center justify-center w-8 h-8"
            >
              <SendHorizonal className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      <div className="px-5 py-5 max-h-[580px] overflow-y-auto">
        <div className="relative pl-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-indigo-100 before:via-border/60 before:to-transparent">
          {filteredEvents.length === 0 ? (
            <div className="text-xs text-muted-foreground py-6 font-medium pl-2">
              No recent changes or comments on this item.
            </div>
          ) : (
            filteredEvents.map((event: any) => {
              const isComment = event.groupType === "Comment";
              const userMeta = userInfo[event.owner] || {};
              const senderName =
                userMeta.fullname || event.owner?.split("@")[0] || event.owner;
              const logStyle = getLogStyles(event.logType);
              return (
                <div
                  key={event.name || Math.random().toString()}
                  className="relative flex items-start gap-4 pb-6 group last:pb-1"
                >
                  <div
                    className={`absolute left-[-22px] top-1.5 z-10 w-4 h-4 rounded-full bg-white border-2 flex items-center justify-center shadow-sm transition-transform duration-200 group-hover:scale-110 ${
                      isComment
                        ? "border-indigo-400 bg-indigo-50"
                        : logStyle.dotBg
                    }`}
                  >
                    {isComment ? (
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                    ) : (
                      logStyle.icon
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    {isComment ? (
                      <div className="bg-card border rounded-lg shadow-sm overflow-hidden">
                        <div className="px-4 py-2.5 bg-muted/30 border-b flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-5 h-5 rounded-full overflow-hidden border border-indigo-100 shrink-0 bg-indigo-50 flex items-center justify-center">
                              <div className="text-[9px] text-indigo-500 font-bold">
                                {senderName.charAt(0).toUpperCase()}
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground font-medium">
                              <span className="font-bold text-foreground">
                                {senderName}
                              </span>
                              <span className="text-muted-foreground font-normal">
                                {" "}
                                shared a response
                              </span>
                              <span className="mx-1 text-border">·</span>
                              <span className="text-muted-foreground font-normal">
                                {timeAgo(event.creation)}
                              </span>
                            </p>
                          </div>
                        </div>
                        <div
                          className="px-4 py-3 text-sm text-foreground leading-relaxed"
                          dangerouslySetInnerHTML={{ __html: event.content }}
                        />
                      </div>
                    ) : (
                      <div className="bg-muted/20 border border-border/40 rounded-lg py-1.5 px-3 flex items-center justify-between gap-4">
                        <p className="text-xs text-muted-foreground leading-relaxed truncate">
                          <span className="font-bold text-foreground">
                            {event.logType === "Like"
                              ? `${senderName} favored this document`
                              : senderName}{" "}
                          </span>
                          <span
                            className="text-muted-foreground"
                            dangerouslySetInnerHTML={{
                              __html:
                                event.logType === "Like" ? "" : event.content,
                            }}
                          />
                        </p>
                        <span className="text-[11px] text-muted-foreground font-medium shrink-0">
                          {timeAgo(event.creation)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export default DocumentActivity;
