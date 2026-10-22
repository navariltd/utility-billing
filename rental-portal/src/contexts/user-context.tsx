/**
 * User context – the authenticated portal user and their Frappe roles.
 *
 * The user identity is read from the Frappe session boot (`frappe.boot.user`),
 * which already contains the roles Frappe resolved for the session, and is
 * enriched with the portal context (linked Customer, portal role). Use
 * `usePortal()` when the portal role or capabilities are needed.
 */

"use client";

import { usePortal } from "@/contexts/portal-context";
import { getBootUser } from "@/lib/portal";
import { GUEST_ROLE, type PortalUser } from "@/types/portal";
import { useFrappeAuth } from "frappe-react-sdk";
import * as React from "react";

interface UserContextValue {
  user: PortalUser | null;
  roles: string[];
  isLoading: boolean;
  isLoggedOut: boolean;
  error: unknown;
  logout: () => Promise<void>;
  /** Re-fetch the portal context (e.g. after the profile was changed). */
  refresh: () => Promise<unknown>;
}

export const UserContext = React.createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const { currentUser, isLoading: authLoading, logout } = useFrappeAuth();
  const { portal, isLoading: portalLoading, error, refresh } = usePortal();

  // The boot payload is rendered with the page, so it only needs to be read once.
  const bootUser = React.useMemo(() => getBootUser(), []);

  const isLoggedOut =
    !authLoading && (!currentUser || currentUser === GUEST_ROLE);

  const user = React.useMemo<PortalUser | null>(() => {
    const name = currentUser || bootUser?.name || portal?.user;

    if (!name || name === GUEST_ROLE) {
      return null;
    }

    return {
      name,
      fullName: portal?.full_name || bootUser?.full_name || name,
      email: portal?.email ?? bootUser?.email ?? null,
      userImage: portal?.user_image ?? bootUser?.user_image ?? null,
      userType: bootUser?.user_type ?? null,
      language: portal?.language ?? bootUser?.language ?? null,
      timeZone: portal?.time_zone ?? bootUser?.time_zone ?? null,
      roles: portal?.roles ?? bootUser?.roles ?? [],
      portalRole: portal?.portal_role ?? GUEST_ROLE,
    };
  }, [currentUser, bootUser, portal]);

  const value = React.useMemo<UserContextValue>(
    () => ({
      user,
      roles: user?.roles ?? [],
      isLoading: authLoading || (portalLoading && !user),
      isLoggedOut: isLoggedOut && !user,
      error,
      logout,
      refresh,
    }),
    [user, authLoading, portalLoading, isLoggedOut, error, logout, refresh],
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

