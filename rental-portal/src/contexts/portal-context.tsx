/**
 * Portal context – the server resolved portal identity of the session.
 *
 * It wraps `utility_billing.api.portal.context.get_portal_context`, which returns
 * the resolved portal role (Tenant, Property Manager, ...), the linked Customer
 * and the capability map that drives the portal navigation. Roles are also taken
 * from the Frappe boot payload so role based routing works before the call
 * resolves.
 */

"use client";

import { can as hasCapability, getBootUserRoles } from "@/lib/portal";
import {
  GUEST_ROLE,
  type PortalCapability,
  type PortalContextData,
} from "@/types/portal";
import { useFrappeGetCall } from "frappe-react-sdk";
import * as React from "react";

interface PortalContextValue {
  /** Server resolved portal context (null while loading or when unavailable). */
  portal: PortalContextData | null;
  isLoading: boolean;
  error: unknown;
  isGuest: boolean;
  isAuthenticated: boolean;
  portalRole: string;
  roles: string[];
  capabilities: Partial<Record<PortalCapability, boolean>>;
  can: (capability: PortalCapability) => boolean;
  refresh: () => Promise<unknown>;
}

export const PortalContext = React.createContext<PortalContextValue | null>(
  null,
);

export function PortalProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading, error, mutate } = useFrappeGetCall<{
    message: PortalContextData;
  }>("utility_billing.api.portal.context.get_portal_context");

  const portal = data?.message ?? null;
  const portalRole = portal?.portal_role ?? GUEST_ROLE;
  const isAuthenticated = Boolean(portal?.user) && portalRole !== GUEST_ROLE;
  const roles = React.useMemo(
    () => portal?.roles ?? getBootUserRoles(),
    [portal?.roles],
  );

  const capabilities = React.useMemo(
    () => portal?.capabilities ?? {},
    [portal?.capabilities],
  );

  const can = React.useCallback(
    (capability: PortalCapability) => hasCapability(capabilities, capability),
    [capabilities],
  );

  const value = React.useMemo<PortalContextValue>(
    () => ({
      portal,
      isLoading: isLoading && !portal,
      error,
      isGuest: !isAuthenticated,
      isAuthenticated,
      portalRole,
      roles,
      capabilities,
      can,
      refresh: () => mutate(),
    }),
    [
      portal,
      isLoading,
      error,
      isAuthenticated,
      portalRole,
      roles,
      capabilities,
      can,
      mutate,
    ],
  );

  return (
    <PortalContext.Provider value={value}>{children}</PortalContext.Provider>
  );
}

export function usePortal() {
  const context = React.useContext(PortalContext);

  if (!context) {
    throw new Error("usePortal must be used within a PortalProvider");
  }

  return context;
}
