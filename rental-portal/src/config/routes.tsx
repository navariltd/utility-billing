/**
 * Application route configuration.
 *
 * Mirrors the nppos dashboard: every route is a plain object so the command
 * search can walk the tree and surface pages marked `searchable`, and dynamic
 * doctype browsing is served by the generic `/app/:doctype(/:id)` routes that
 * render `DocTypeList` / `DocTypeForm` on top of the standard Frappe APIs.
 */

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

const Notifications = lazy(() => import("@/app/settings/notifications/page"));

const PropertyDetails = lazy(() => import("@/app/properties/[property]/page"));
const PropertyBooking = lazy(
  () => import("@/app/properties/[property]/book/page"),
);
const MyProperties = lazy(() => import("@/app/my-properties/page"));

// Generic doctype pages (list and detail) driven by the doctype slug.
const DocTypeListPage = lazy(() => import("@/app/doctype/DocTypeListPage"));
const DocTypeFormPage = lazy(() => import("@/app/doctype/DocTypeFormPage"));

import { ProtectedRoute } from "@/app/auth/protected-route";
import { RoleProtectedRoute } from "@/app/auth/role-protected-route";

export interface RouteConfig {
  path?: string;
  element: React.ReactNode;
  children?: RouteConfig[];
  protected?: boolean;
  roles?: string[];
  index?: boolean;
  /**
   * When true, this page appears in the command-search "App Pages" results.
   * Defaults to false (opt-in).
   */
  searchable?: boolean;
  /**
   * Human-friendly label shown in the command-search results. Falls back to a
   * slug-derived title when omitted.
   */
  searchTitle?: string;
}

/**
 * When true, dynamic doctype browsing via the `/app/:doctype` routes is enabled
 * and the command search surfaces "New X" / "X List" results linking to them.
 */
export const APP_PAGES_ENABLED = true;

export const routes: RouteConfig[] = [
  {
    path: "/",
    element: <Navigate to="/dashboard" replace />,
    searchable: false,
  },
  {
    path: "/auth/sign-in",
    element: <SignIn />,
    searchable: false,
  },
  {
    path: "/auth/sign-up",
    element: <SignUp />,
    searchable: false,
  },
  {
    path: "/auth/forgot-password",
    element: <ForgotPassword />,
    searchable: false,
  },
  // Public property browsing (also available to guests).
  {
    path: "/properties",
    element: <PropertyList />,
    searchable: true,
    searchTitle: "Properties",
  },
  {
    path: "/properties/:property",
    element: <PropertyDetails />,
    searchable: false,
  },
  {
    path: "/properties/:property/book",
    element: (
      <ProtectedRoute>
        <PropertyBooking />
      </ProtectedRoute>
    ),
    searchable: false,
  },
  // Authenticated portal pages.
  {
    path: "/dashboard",
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
    searchable: true,
    searchTitle: "Dashboard",
  },
  {
    path: "/my-properties",
    element: (
      <ProtectedRoute>
        <MyProperties />
      </ProtectedRoute>
    ),
    searchable: true,
    searchTitle: "My Properties",
  },
  {
    path: "/settings/notifications",
    element: (
      <ProtectedRoute>
        <Notifications />
      </ProtectedRoute>
    ),
    searchable: true,
    searchTitle: "Notifications",
  },
  // Dynamic doctype routes, e.g. /app/user/Administrator or /app/contract/new.
  {
    path: "/app/:doctype",
    element: (
      <ProtectedRoute>
        <DocTypeListPage />
      </ProtectedRoute>
    ),
    searchable: false,
  },
  {
    path: "/app/:doctype/:id",
    element: (
      <ProtectedRoute>
        <DocTypeFormPage />
      </ProtectedRoute>
    ),
    searchable: false,
  },
  {
    path: "/users",
    element: (
      <RoleProtectedRoute roles={["System Manager", "Administrator"]}>
        <UsersPage />
      </RoleProtectedRoute>
    ),
    searchable: true,
    searchTitle: "Users",
  },
  // Error pages (public)
  {
    path: "/errors/unauthorized",
    element: <Unauthorized />,
    searchable: false,
  },
  {
    path: "/errors/forbidden",
    element: <Forbidden />,
    searchable: false,
  },
  {
    path: "/errors/not-found",
    element: <NotFound />,
    searchable: false,
  },
  {
    path: "/errors/internal-server-error",
    element: <InternalServerError />,
    searchable: false,
  },
  {
    path: "*",
    element: <NotFound />,
    searchable: false,
  },
];
