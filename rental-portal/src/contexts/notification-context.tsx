"use client";

import { useFrappeGetCall } from "frappe-react-sdk";
import * as React from "react";

interface NotificationLog {
  name: string;
  title: string;
  subject: string;
  read: number;
  creation: string;
}

interface NotificationContextValue {
  unreadCount: number;
  notificationLogs: NotificationLog[];
  refreshNotifications: () => void;
  isLoading: boolean;
}

export const NotificationContext =
  React.createContext<NotificationContextValue | null>(null);

export function NotificationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const {
    data: responseData,
    mutate: refreshNotifications,
    isLoading,
  } = useFrappeGetCall(
    "frappe.desk.doctype.notification_log.notification_log.get_notification_logs",
    { limit: 500 },
    "rental-portal-notifications-list",
  );

  const notificationLogs: NotificationLog[] =
    responseData?.message?.notification_logs || [];

  const unreadCount = React.useMemo(
    () => notificationLogs.filter((log) => log.read === 0).length,
    [notificationLogs],
  );

  const value = React.useMemo(
    () => ({
      unreadCount,
      notificationLogs,
      refreshNotifications,
      isLoading,
    }),
    [unreadCount, notificationLogs, refreshNotifications, isLoading],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextValue {
  const context = React.useContext(NotificationContext);
  if (!context) {
    throw new Error(
      "useNotifications must be used within a NotificationProvider",
    );
  }
  return context;
}