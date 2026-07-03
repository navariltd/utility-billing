import PropertyList from "@/app/properties/page";
import UsersPage from "@/app/users/page";
import { lazy } from "react";
import { Navigate } from "react-router-dom";

const SignIn = lazy(() => import("@/app/auth/sign-in/page"));
const SignUp = lazy(() => import("@/app/auth/sign-up/page"));
const ForgotPassword = lazy(() => import("@/app/auth/forgot-password/page"));

const Unauthorized = lazy(() => import("@/app/errors/unauthorized/page"));
const Forbidden = lazy(() => import("@/app/errors/forbidden/page"));
const NotFound = lazy(() => import("@/app/errors/not-found/page"));
const InternalServerError = lazy(
  () => import("@/app/errors/internal-server-error/page"),
);
const Dashboard = lazy(() => import("@/app/dashboard/page"));

const UserSettings = lazy(() => import("@/app/settings/user/page"));
const AccountSettings = lazy(() => import("@/app/settings/account/page"));
const NotificationSettings = lazy(
  () => import("@/app/settings/notifications/page"),
);

const PropertyDetails = lazy(() => import("@/app/properties/[property]/page"));
const PropertyBooking = lazy(
  () => import("@/app/properties/[property]/book/page"),
);

import { ProtectedRoute } from "@/app/auth/protected-route";
import { RoleProtectedRoute } from "@/app/auth/role-protected-route";

export interface RouteConfig {
  path: string;
  element: React.ReactNode;
  children?: RouteConfig[];
  protected?: boolean;
  roles?: string[];
}

export const routes: RouteConfig[] = [
  {
    path: "/",
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: "/auth/sign-in",
    element: <SignIn />,
  },
  {
    path: "/auth/sign-up",
    element: <SignUp />,
  },
  {
    path: "/auth/forgot-password",
    element: <ForgotPassword />,
  },
  {
    path: "/dashboard",
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
  },
  {
    path: "/properties",
    element: <PropertyList />,
  },
  {
    path: "/properties/:property",
    element: <PropertyDetails />,
  },
  {
    path: "/properties/:property/book",
    element: (
      <ProtectedRoute>
        <PropertyBooking />
      </ProtectedRoute>
    ),
  },
  {
    path: "/users",
    element: (
      <RoleProtectedRoute roles={["System Manager", "Administrator"]}>
        <UsersPage />
      </RoleProtectedRoute>
    ),
  },
  {
    path: "/settings/user",
    element: (
      <ProtectedRoute>
        <UserSettings />
      </ProtectedRoute>
    ),
  },
  {
    path: "/settings/account",
    element: (
      <ProtectedRoute>
        <AccountSettings />
      </ProtectedRoute>
    ),
  },
  {
    path: "/settings/notifications",
    element: (
      <ProtectedRoute>
        <NotificationSettings />
      </ProtectedRoute>
    ),
  },
  // Error pages (public)
  {
    path: "/errors/unauthorized",
    element: <Unauthorized />,
  },
  {
    path: "/errors/forbidden",
    element: <Forbidden />,
  },
  {
    path: "/errors/not-found",
    element: <NotFound />,
  },
  {
    path: "/errors/internal-server-error",
    element: <InternalServerError />,
  },
  {
    path: "*",
    element: <NotFound />,
  },
];
