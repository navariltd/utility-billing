/**
 * Global permission guard for Frappe 403 responses.
 *
 * Intercepts all HTTP fetch requests and redirects to the appropriate page
 * when a 403 PermissionError is received. Unauthenticated users are sent to
 * the sign-in page; authenticated users without permission go to the 403 page.
 *
 * Dependencies:
 *   - react-router-dom for navigation
 *   - the Frappe session boot (`frappe.boot.user`) for auth state detection
 */

"use client";

import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

interface PermissionGuardProps {
  children: React.ReactNode;
}

/**
 * Check whether a session user is present in the Frappe boot payload.
 */
function isUserLoggedIn(): boolean {
  const user = (window as unknown as { frappe?: { boot?: { user?: { name?: string } } } })
    .frappe?.boot?.user?.name;

  return Boolean(user && user !== "Guest");
}

export function PermissionGuard({ children }: PermissionGuardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const redirectedRef = useRef(false);
  const originalFetchRef = useRef<typeof globalThis.fetch | null>(null);

  useEffect(() => {
    if (originalFetchRef.current) return;

    originalFetchRef.current = window.fetch;

    const interceptedFetch = async (
      input: RequestInfo | URL,
      init?: RequestInit,
    ): Promise<Response> => {
      const response = await originalFetchRef.current!(input, init);

      if (
        response.status === 403 &&
        !redirectedRef.current &&
        !location.pathname.includes("/errors/") &&
        !location.pathname.includes("/auth/")
      ) {
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json") || contentType.includes("text/plain")) {
          try {
            const clone = response.clone();
            const body = await clone.text();
            if (
              body.includes("PermissionError") ||
              body.includes("Not permitted") ||
              body.includes("Insufficient Permission") ||
              body.includes("not allowed")
            ) {
              redirectedRef.current = true;
              if (isUserLoggedIn()) {
                navigate("/errors/forbidden", { replace: true });
              } else {
                const currentPath = location.pathname + location.search;
                const encodedRedirect = encodeURIComponent(currentPath);
                navigate(`/auth/sign-in?redirect-to=${encodedRedirect}`, { replace: true });
              }
            }
          } catch {
            // Response body already consumed
          }
        }
      }

      return response;
    };

    window.fetch = interceptedFetch;

    return () => {
      if (originalFetchRef.current) {
        window.fetch = originalFetchRef.current;
        originalFetchRef.current = null;
      }
    };
  }, [navigate, location.pathname]);

  useEffect(() => {
    redirectedRef.current = false;
  }, [location.pathname]);

  return <>{children}</>;
}