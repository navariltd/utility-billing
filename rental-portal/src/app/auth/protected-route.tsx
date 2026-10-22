/**
 * Route guard for authenticated portal pages.
 *
 * Unauthenticated visitors are redirected to the sign-in page with the original
 * path preserved in `redirect-to`, so they return to where they came from.
 */

import { useUser } from "@/contexts/user-context";
import { Skeleton } from "@/components/ui/skeleton";
import { hasAnyRole } from "@/lib/portal";
import { Navigate, useLocation } from "react-router-dom";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Frappe roles allowed to view the page. Empty means "any authenticated user". */
  requiredRoles?: string[];
}

function SkeletonContent() {
  return (
    <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6 px-4 lg:px-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-72" />
      <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="h-[400px] w-full rounded-lg" />
        <Skeleton className="h-[600px] w-full rounded-lg lg:col-span-2" />
      </div>
    </div>
  );
}

export function ProtectedRoute({
  children,
  requiredRoles = [],
}: ProtectedRouteProps) {
  const { user, isLoading, isLoggedOut } = useUser();
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

  if (!hasAnyRole(user.roles, requiredRoles) && requiredRoles.length > 0) {
    return <Navigate to="/errors/forbidden" replace />;
  }

  return <>{children}</>;
}

