"use client";

import { BellDot, CircleUser, EllipsisVertical, LogOut, Palette } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Logo } from "@/components/logo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { useNotifications } from "@/contexts/notification-context";
import { useUser } from "@/contexts/user-context";
import { useFrappeAuth } from "frappe-react-sdk";
import { useState } from "react";
import { toast } from "sonner";

export function NavUser({
  user,
  onLogout,
  onOpenCustomizer,
}: {
  user: {
    name: string;
    email: string;
    avatar: string;
  };
  /** Logout handler from the user context; falls back to `useFrappeAuth`. */
  onLogout?: () => Promise<void>;
  /** Opens the theme customizer mounted by the page layout. */
  onOpenCustomizer?: () => void;
}) {
  const { isMobile } = useSidebar();
  const { logout: frappeLogout } = useFrappeAuth();
  const { unreadCount } = useNotifications();
  const { user: portalUser } = useUser();
  const logout = onLogout ?? frappeLogout;
  const navigate = useNavigate();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // nppos approach: the account entry opens the generic User doctype form, where
  // the profile and the password can be maintained through standard Frappe APIs.
  const accountUrl = `/app/user/${encodeURIComponent(portalUser?.name || user.name)}`;

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);
      await logout();
      navigate("/auth/sign-in");
    } catch {
      toast.error("Could not log out. Please try again.");
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground cursor-pointer"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg">
                <Logo size={28} />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{user.name}</span>
                <span className="text-muted-foreground truncate text-xs">
                  {user.email}
                </span>
              </div>
              <EllipsisVertical className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
            side={isMobile ? "bottom" : "right"}
            align="end"
            sideOffset={4}
          >
            <DropdownMenuLabel className="p-0 font-normal">
              <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                <div className="h-8 w-8 rounded-lg">
                  <Logo size={28} />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{user.name}</span>
                  <span className="text-muted-foreground truncate text-xs">
                    {user.email}
                  </span>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem asChild className="cursor-pointer">
                <Link to={accountUrl}>
                  <CircleUser />
                  Account
                </Link>
              </DropdownMenuItem>
              {onOpenCustomizer && (
                <DropdownMenuItem
                  className="cursor-pointer"
                  onSelect={(event) => {
                    event.preventDefault();
                    // Small delay so the dropdown closes before the sheet opens.
                    setTimeout(onOpenCustomizer, 50);
                  }}
                >
                  <Palette />
                  Customize Theme
                </DropdownMenuItem>
              )}
              <DropdownMenuItem asChild className="cursor-pointer">
                <Link
                  to="/settings/notifications"
                  className="flex w-full items-center justify-between"
                >
                  <span className="flex items-center gap-2">
                    <BellDot />
                    <span>Notifications</span>
                  </span>
                  {unreadCount > 0 && (
                    <span className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1.5 text-[10px] font-bold leading-none text-white ring-2 ring-white shadow-sm">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  )}
                </Link>
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer"
              onClick={handleLogout}
              disabled={isLoggingOut}
            >
              <LogOut className={isLoggingOut ? "animate-spin" : ""} />
              {isLoggingOut ? "Logging out..." : "Log out"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
