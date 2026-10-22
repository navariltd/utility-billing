/**
 * Notifications feed.
 *
 * Mirrors the nppos notifications page: the notification log is read through the
 * standard `frappe.desk.doctype.notification_log.notification_log.get_notification_logs`
 * endpoint (see `NotificationProvider`) and rendered as a list with a detail
 * panel. Delivery preferences live on the preferences page.
 */

"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useNotifications } from "@/contexts/notification-context";
import { useUser } from "@/contexts/user-context";
import { Bell, ChevronLeft, RefreshCw, Settings2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

interface NotificationLog {
  name: string;
  title: string;
  subject: string;
  read: number;
  creation: string;
}

export default function NotificationSettings() {
  const { notificationLogs, unreadCount, refreshNotifications, isLoading } =
    useNotifications();
  const { user } = useUser();
  const [selected, setSelected] = useState<NotificationLog | null>(null);

  // Delivery preferences live on the user's own `Notification Settings` record;
  // the generic doctype form handles them (no custom portal page).
  const preferencesUrl = user
    ? `/app/notification-settings/${encodeURIComponent(user.name)}`
    : null;

  return (
    <BaseLayout
      title="Notifications"
      description={
        unreadCount > 0
          ? `${unreadCount} unread notification${unreadCount > 1 ? "s" : ""}`
          : "All caught up!"
      }
    >
      <div className="flex flex-col px-4 lg:px-6">
        {/* Toolbar */}
        <div className="mb-6 flex shrink-0 items-center justify-end gap-2">
          {preferencesUrl && (
            <Button
              variant="outline"
              size="sm"
              className="cursor-pointer"
              asChild
            >
              <Link to={preferencesUrl}>
                <Settings2 className="mr-2 h-4 w-4" />
                Preferences
              </Link>
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="cursor-pointer"
            onClick={() => refreshNotifications()}
            disabled={isLoading}
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")} />
            Refresh
          </Button>
        </div>

        {/* Content area */}
        <div className="flex min-h-0 flex-1 gap-6">
          {/* List */}
          <div className={cn("flex min-h-0 flex-col", selected ? "w-1/2" : "w-full")}>
          {isLoading && notificationLogs.length === 0 ? (
            <div className="space-y-3 overflow-y-auto pr-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-xl border bg-card p-4 animate-pulse"
                >
                  <div className="h-4 w-4 rounded-full bg-muted shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 rounded bg-muted" />
                    <div className="h-3 w-1/3 rounded bg-muted" />
                  </div>
                </div>
              ))}
            </div>
          ) : notificationLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                <Bell className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold">No notifications</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                You're all up to date. Notifications will appear here when they
                arrive.
              </p>
            </div>
          ) : (
            <div className="space-y-2 overflow-y-auto pr-2">
              {notificationLogs.map((notification) => {
                const isSelected = selected?.name === notification.name;
                return (
                  <button
                    key={notification.name}
                    type="button"
                    onClick={() =>
                      setSelected(
                        isSelected ? null : notification,
                      )
                    }
                    className={cn(
                      "w-full text-left rounded-xl border p-4 transition-all cursor-pointer",
                      isSelected
                        ? "border-primary/50 bg-primary/[0.04] ring-1 ring-primary/20 shadow-sm"
                        : notification.read
                          ? "bg-card hover:bg-accent/50 border-border/60"
                          : "bg-card border-border font-medium shadow-sm",
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="relative mt-0.5 shrink-0">
                        <Bell
                          className={cn(
                            "h-4 w-4",
                            notification.read
                              ? "text-muted-foreground"
                              : "text-foreground",
                          )}
                        />
                        {!notification.read && (
                          <span className="absolute -top-1 -right-1.5 block h-2 w-2 rounded-full bg-primary ring-2 ring-background" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div
                          className={cn(
                            "text-sm leading-relaxed [&>strong]:font-semibold [&>.subject-title]:font-semibold [&>.subject-title]:text-primary",
                            notification.read
                              ? "text-muted-foreground"
                              : "text-foreground",
                          )}
                          dangerouslySetInnerHTML={{
                            __html:
                              (notification.title || notification.subject || "").length > 120
                                ? (notification.title || notification.subject || "").slice(0, 120) + "…"
                                : notification.title || notification.subject || "",
                          }}
                        />
                        <p className="mt-1.5 text-xs text-muted-foreground">
                          {new Date(notification.creation).toLocaleDateString(
                            "en-US",
                            {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            },
                          )}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selected && (
          <div className="w-1/2 min-w-0 overflow-y-auto">
            <div className="rounded-xl border bg-card shadow-sm">
              {/* Detail header */}
              <div className="flex items-center gap-2 border-b px-5 py-3">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 cursor-pointer"
                  onClick={() => setSelected(null)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm font-medium">Notification Details</span>
              </div>

              {/* Detail body */}
              <div className="px-5 py-5 space-y-5">
                <div className="flex items-start gap-4">
                  <div className="shrink-0 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                    <Bell className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <div
                      className="text-sm leading-relaxed [&>strong]:font-semibold [&>.subject-title]:font-semibold [&>.subject-title]:text-primary"
                      dangerouslySetInnerHTML={{
                        __html: selected.title || selected.subject || "",
                      }}
                    />
                    <p className="mt-3 text-xs text-muted-foreground">
                      {new Date(selected.creation).toLocaleDateString("en-US", {
                        weekday: "short",
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                    Full Message
                  </h4>
                  <div
                    className="text-sm leading-relaxed text-foreground [&>strong]:font-semibold [&>.subject-title]:font-semibold [&>.subject-title]:text-primary"
                    dangerouslySetInnerHTML={{
                      __html: selected.subject || selected.title || "",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
        </div>
      </div>
    </BaseLayout>
  );
}
