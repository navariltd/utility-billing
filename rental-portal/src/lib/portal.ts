/**
 * Accessors for the Frappe session boot embedded in the portal page.
 *
 * The boot payload is built by Frappe itself (`frappe.sessions.get()`), therefore
 * the portal reads the session user and the user's roles from `frappe.boot.user`
 * instead of relying on a custom endpoint or on `User` document permissions
 * (which Website Users do not have).
 */

import {
  GUEST_ROLE,
  type BootUser,
  type PortalCapability,
} from "@/types/portal";

interface FrappeBoot {
  user?: BootUser;
}

interface FrappeGlobal {
  boot?: FrappeBoot;
}

/** Return `window.frappe.boot` when the page was served through Frappe. */
export function getFrappeBoot(): FrappeBoot | null {
  const frappe = (window as unknown as { frappe?: FrappeGlobal }).frappe;

  return frappe?.boot ?? null;
}

/**
 * Return the boot user for the current session.
 *
 * @returns the user from the boot payload, or `null` for guests / unresolved sessions.
 */
export function getBootUser(): BootUser | null {
  const user = getFrappeBoot()?.user;

  if (!user?.name || user.name === GUEST_ROLE) {
    return null;
  }

  return user;
}

/** Return the Frappe roles of the boot user (`[]` for guests). */
export function getBootUserRoles(): string[] {
  return getBootUser()?.roles ?? [];
}

/** Return `true` when `roles` contains at least one of `candidates`. */
export function hasAnyRole(roles: string[] = [], candidates: string[]): boolean {
  return candidates.some((role) => roles.includes(role));
}

/** Return `true` when the given portal context grants `capability`. */
export function can(
  capabilities: Partial<Record<PortalCapability, boolean>> | undefined,
  capability: PortalCapability,
): boolean {
  return Boolean(capabilities?.[capability]);
}
