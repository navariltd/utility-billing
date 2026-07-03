import { useUser } from "@/contexts/user-context";
import { Navigate } from "react-router-dom";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

export function ProtectedRoute({
  children,
  requiredRoles = [],
}: ProtectedRouteProps) {
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

  if (requiredRoles.length > 0) {
    const userRoles = user.roles?.map((role: any) => role.role) || [];
    const hasRequiredRole = requiredRoles.some((role) =>
      userRoles.includes(role),
    );

    if (!hasRequiredRole) {
      return <Navigate to="/errors/forbidden" replace />;
    }
  }

  return <>{children}</>;
}
