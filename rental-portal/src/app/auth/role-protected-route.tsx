/**
 * Route guard for pages restricted to specific Frappe or portal roles.
 *
 * Portal roles (Tenant, Property Manager, ...) are resolved server side by
 * `utility_billing.api.portal.context`; Frappe roles come from the session boot.
 */

import { Skeleton } from "@/components/ui/skeleton";
import { usePortal } from "@/contexts/portal-context";
import { useUser } from "@/contexts/user-context";
import { hasAnyRole } from "@/lib/portal";
import { Navigate, useLocation } from "react-router-dom";

interface RoleProtectedRouteProps {
  children: React.ReactNode;
  /** Frappe roles allowed to view the page. */
  roles?: string[];
  /** Portal roles allowed to view the page. */
  portalRoles?: string[];
  redirectTo?: string;
}

function SkeletonContent() {
  return (
    <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6 px-4 lg:px-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-72" />
      <Skeleton className="mt-4 h-[600px] w-full rounded-lg" />
    </div>
  );
}

export function RoleProtectedRoute({
  children,
  roles = [],
  portalRoles = [],
  redirectTo = "/errors/forbidden",
}: RoleProtectedRouteProps) {
  const { user, isLoading, isLoggedOut } = useUser();
  const { portalRole } = usePortal();
  const location = useLocation();

  if (isLoading) {
    return <SkeletonContent />;
  }

  if (isLoggedOut || !user) {
    const currentPath = location.pathname + location.search;
    const encodedRedirect = encodeURIComponent(currentPath);

    return (
      <Navigate to={`/auth/sign-in?redirect-to=${encodedRedirect}`} replace />
    );
  }

  const hasFrappeRole = hasAnyRole(user.roles, roles);
  const hasPortalRole = portalRoles.length > 0 && portalRoles.includes(portalRole);

  if (!hasFrappeRole && !hasPortalRole) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}

