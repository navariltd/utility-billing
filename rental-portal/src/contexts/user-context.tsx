"use client";

import { useFrappeAuth, useFrappeGetDoc } from "frappe-react-sdk";
import * as React from "react";

interface UserContextValue {
  user: any | null;
  isLoading: boolean;
  error: any;
  logout: () => Promise<void>;
}

export const UserContext = React.createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const { currentUser, isLoading: authLoading, logout } = useFrappeAuth();

  const {
    data: userData,
    error: userError,
    isValidating: userLoading,
  } = useFrappeGetDoc<any>("User", currentUser || "Guest");

  const user = React.useMemo(() => {
    if (!currentUser && !authLoading) return null;
    if (!userData) return null;

    return {
      ...userData,
    };
  }, [userData, currentUser, authLoading]);

  const value = React.useMemo(
    () => ({
      user,
      isLoading: authLoading || userLoading,
      error: userError,
      logout,
    }),
    [user, authLoading, userLoading, userError, logout],
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const context = React.useContext(UserContext);
  if (!context) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}
