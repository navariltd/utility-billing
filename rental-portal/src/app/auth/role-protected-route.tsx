import { useUser } from "@/contexts/user-context";
import { Navigate } from "react-router-dom";

interface RoleProtectedRouteProps {
  children: React.ReactNode;
  roles: string[];
  redirectTo?: string;
}

export function RoleProtectedRoute({
  children,
  roles,
  redirectTo = "/errors/forbidden",
}: RoleProtectedRouteProps) {
  const { user, isLoading } = useUser();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth/sign-in" replace />;
  }

  const userRoles = user.roles?.map((role: any) => role.role) || [];
  const hasAccess = roles.some((role) => userRoles.includes(role));

  if (!hasAccess) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}
