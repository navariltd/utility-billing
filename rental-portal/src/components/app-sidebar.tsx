"use client";

/**
 * Application sidebar.
 *
 * Navigation is driven by the portal context: guests only see the public
 * property browser, authenticated portal users see the pages their capabilities
 * grant them, and user administration is limited to System Managers and
 * Administrators.
 */

import { Logo } from "@/components/logo";
import { NavMain } from "@/components/nav-main";
import { NavUser } from "@/components/nav-user";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortal } from "@/contexts/portal-context";
import { useUser } from "@/contexts/user-context";
import { hasAnyRole } from "@/lib/portal";
import type { PortalCapability } from "@/types/portal";
import {
  Bell,
  Building2,
  Home,
  LayoutDashboard,
  LogIn,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

interface NavItem {
  title: string;
  url: string;
  icon: LucideIcon;
  capability?: PortalCapability;
  /** Frappe roles allowed to see the item. */
  roles?: string[];
}

const publicNavGroups: { label: string; items: NavItem[] }[] = [
  {
    label: "Explore",
    items: [{ title: "Properties", url: "/properties", icon: Home }],
  },
];

const privateNavGroups: { label: string; items: NavItem[] }[] = [
  {
    label: "Main",
    items: [
      {
        title: "Dashboard",
        url: "/dashboard",
        icon: LayoutDashboard,
        capability: "view_dashboard",
      },
      { title: "Properties", url: "/properties", icon: Home },
      {
        title: "My Properties",
        url: "/my-properties",
        icon: Building2,
        capability: "view_my_units",
      },
    ],
  },
  {
    label: "Account",
    items: [
      {
        title: "Notifications",
        url: "/settings/notifications",
        icon: Bell,
        capability: "manage_notifications",
      },
    ],
  },
  {
    label: "User Management",
    items: [
      {
        title: "Users",
        url: "/users",
        icon: Users,
        roles: ["System Manager", "Administrator"],
      },
    ],
  },
];

function SidebarSkeleton() {
  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" disabled>
              <Skeleton className="size-8 rounded-lg" />
              <div className="grid flex-1 gap-1 text-left text-sm leading-tight">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-3 w-28" />
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {[1, 2].map((section) => (
          <div key={section} className="px-3 py-2">
            <Skeleton className="mb-3 h-4 w-24" />
            <div className="space-y-1">
              {[1, 2, 3].map((item) => (
                <Skeleton key={item} className="h-8 w-full rounded-md" />
              ))}
            </div>
          </div>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center gap-2 p-2">
          <Skeleton className="size-8 rounded-full" />
          <div className="grid flex-1 gap-1">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}


export function AppSidebar({
  onOpenCustomizer,
  ...props
}: React.ComponentProps<typeof Sidebar> & { onOpenCustomizer?: () => void }) {
  const { user, isLoading, logout } = useUser();
  const { portalRole, can } = usePortal();

  const isAuthenticated = Boolean(user);

  const visibleNavGroups = React.useMemo(() => {
    if (!isAuthenticated) {
      return publicNavGroups;
    }

    return privateNavGroups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => {
          if (item.roles && !hasAnyRole(user?.roles, item.roles)) {
            return false;
          }

          return !item.capability || can(item.capability);
        }),
      }))
      .filter((group) => group.items.length > 0);
  }, [isAuthenticated, user?.roles, can]);

  if (isLoading) {
    return <SidebarSkeleton />;
  }

  return (
    <Sidebar {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link to={isAuthenticated ? "/dashboard" : "/properties"}>
                <div className="bg-primary text-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <Logo size={24} className="text-current" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">Rental Billing</span>
                  <span className="truncate text-xs">
                    {isAuthenticated ? `${portalRole} Portal` : "Welcome"}
                  </span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {visibleNavGroups.map((group) => (
          <NavMain key={group.label} label={group.label} items={group.items} />
        ))}
      </SidebarContent>
      <SidebarFooter>
        {user ? (
          <NavUser
            user={{
              name: user.fullName || user.name,
              email: user.email || user.name,
              avatar: user.userImage || "",
            }}
            onLogout={logout}
            onOpenCustomizer={onOpenCustomizer}
          />
        ) : (
          <div className="p-2">
            <Link
              to="/auth/sign-in"
              className="hover:bg-accent hover:text-accent-foreground flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-all"
            >
              <LogIn className="h-4 w-4" />
              <span>Sign In</span>
            </Link>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}

